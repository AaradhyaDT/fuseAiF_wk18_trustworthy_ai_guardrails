"""Output Schema Validator: Strict JSON & Pydantic Conformance Gate."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from guardrails.models import SchemaValidationResult


class OutputSchemaValidator:
    """Validates generative model output against structured schema constraints.

    Extracts JSON from markdown code blocks or surrounding prose, validates types
    and required fields, and constructs corrective retry prompts on failure.
    """

    JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

    def extract_json(self, text: str) -> str | None:
        """Isolate JSON payload from markdown fences or bare brackets."""
        # 1. Try markdown code block
        match = self.JSON_BLOCK_PATTERN.search(text)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate

        # 2. Try raw text directly
        stripped = text.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            return stripped

        # 3. Find outermost curly braces
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        # 4. Find outermost brackets for lists
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        return None

    def validate(
        self,
        output_text: str,
        expected_schema: dict[str, Any] | type[BaseModel] | None = None,
    ) -> SchemaValidationResult:
        """Validate output text against expected schema constraints."""
        json_str = self.extract_json(output_text)
        if json_str is None:
            return SchemaValidationResult(
                passed=False,
                errors=["No JSON structure found in output."],
                retry_prompt=self._build_retry_prompt(
                    "The output did not contain any valid JSON structure. Please format your entire response as a valid JSON object.",
                    expected_schema,
                ),
            )

        # Parse JSON syntax
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as exc:
            return SchemaValidationResult(
                passed=False,
                errors=[f"Invalid JSON syntax: {exc.msg} at line {exc.lineno} col {exc.colno}"],
                retry_prompt=self._build_retry_prompt(
                    f"Syntax error in JSON: {exc.msg}. Please fix the syntax error and output valid JSON.",
                    expected_schema,
                ),
            )

        if not isinstance(parsed, (dict, list)):
            return SchemaValidationResult(
                passed=False,
                errors=["Output must be a JSON object or array."],
                retry_prompt=self._build_retry_prompt(
                    "The parsed JSON was a scalar value. It must be an object or list.",
                    expected_schema,
                ),
            )

        # No schema provided -> JSON syntax validity is sufficient
        if expected_schema is None:
            return SchemaValidationResult(
                passed=True,
                parsed_json=parsed,
            )

        # -------------------------------------------------------------
        # Pydantic Model Validation
        # -------------------------------------------------------------
        if isinstance(expected_schema, type) and issubclass(expected_schema, BaseModel):
            if not isinstance(parsed, dict):
                return SchemaValidationResult(
                    passed=False,
                    errors=["Schema expects a JSON object matching the Pydantic model."],
                    retry_prompt=self._build_retry_prompt(
                        "Expected a JSON object, but received an array.",
                        expected_schema,
                    ),
                )
            try:
                validated_model = expected_schema.model_validate(parsed)
                return SchemaValidationResult(
                    passed=True,
                    parsed_json=validated_model.model_dump(),
                )
            except ValidationError as err:
                errors = [f"{e['loc']}: {e['msg']}" for e in err.errors()]
                return SchemaValidationResult(
                    passed=False,
                    errors=errors,
                    parsed_json=parsed,
                    retry_prompt=self._build_retry_prompt(
                        f"Schema validation failed: {'; '.join(errors)}",
                        expected_schema,
                    ),
                )

        # -------------------------------------------------------------
        # JSON Schema Dict Validation
        # -------------------------------------------------------------
        errors = self._validate_dict_schema(parsed, expected_schema)
        if errors:
            return SchemaValidationResult(
                passed=False,
                errors=errors,
                parsed_json=parsed,
                retry_prompt=self._build_retry_prompt(
                    f"Schema constraints violated: {'; '.join(errors)}",
                    expected_schema,
                ),
            )

        return SchemaValidationResult(
            passed=True,
            parsed_json=parsed,
        )

    def _validate_dict_schema(self, data: Any, schema: dict[str, Any]) -> list[str]:
        """Verify dictionary data against JSON Schema dict."""
        errors: list[str] = []
        expected_type = schema.get("type")

        if expected_type == "object":
            if not isinstance(data, dict):
                return ["Expected JSON object, got " + type(data).__name__]

            # Required fields
            required = schema.get("required", [])
            for field in required:
                if field not in data:
                    errors.append(f"Missing required field: '{field}'")

            # Field property types
            properties = schema.get("properties", {})
            for key, prop_schema in properties.items():
                if key in data:
                    val = data[key]
                    prop_type = prop_schema.get("type")
                    if prop_type == "string" and not isinstance(val, str):
                        errors.append(f"Field '{key}' must be a string, got {type(val).__name__}")
                    elif prop_type in ("number", "integer") and not isinstance(val, (int, float)):
                        errors.append(f"Field '{key}' must be numeric, got {type(val).__name__}")
                    elif prop_type == "boolean" and not isinstance(val, bool):
                        errors.append(f"Field '{key}' must be boolean, got {type(val).__name__}")
                    elif prop_type == "array" and not isinstance(val, list):
                        errors.append(f"Field '{key}' must be an array, got {type(val).__name__}")

        elif expected_type == "array" and not isinstance(data, list):
            errors.append("Expected JSON array, got " + type(data).__name__)

        return errors

    def _build_retry_prompt(
        self,
        error_explanation: str,
        expected_schema: dict[str, Any] | type[BaseModel] | None,
    ) -> str:
        """Construct corrective prompt instructing model how to rectify schema violation."""
        schema_desc = ""
        if isinstance(expected_schema, type) and issubclass(expected_schema, BaseModel):
            schema_desc = json.dumps(expected_schema.model_json_schema(), indent=2)
        elif isinstance(expected_schema, dict):
            schema_desc = json.dumps(expected_schema, indent=2)

        prompt = (
            f"Your previous response had formatting/schema errors:\n"
            f"{error_explanation}\n\n"
        )
        if schema_desc:
            prompt += (
                f"You must conform strictly to this JSON Schema:\n"
                f"```json\n{schema_desc}\n```\n\n"
            )
        prompt += (
            "Please output ONLY valid JSON without any markdown explanations outside the code block."
        )
        return prompt
