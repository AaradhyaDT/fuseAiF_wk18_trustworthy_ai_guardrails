"""Output Guardrail Pipeline: Unified Post-LLM Verification."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from guardrails.input.injection_detector import CanaryTokenManager
from guardrails.models import OutputGuardrailReport
from guardrails.output.groundedness_checker import DomainType, GroundednessChecker
from guardrails.output.leak_scrubber import OutputLeakScrubber
from guardrails.output.schema_validator import OutputSchemaValidator


class OutputGuardrailPipeline:
    """Orchestrates output guardrail stages sequentially in cheapest-first order.

    Stages:
    1. Schema Validation: Structural conformance and type enforcement.
    2. Groundedness & Hallucination: Claim extraction & context entailment check.
    3. Leak Scrubber: Canary token verification and PII data leakage suppression.
    """

    def __init__(
        self,
        canary_manager: CanaryTokenManager | None = None,
        default_domain: DomainType = "general",
    ) -> None:
        self.schema_validator = OutputSchemaValidator()
        self.groundedness_checker = GroundednessChecker()
        self.leak_scrubber = OutputLeakScrubber(canary_manager=canary_manager)
        self.default_domain = default_domain

    def run(
        self,
        output_text: str,
        source_context: str | None = None,
        expected_schema: dict[str, Any] | type[BaseModel] | None = None,
        domain: DomainType | None = None,
        redact_pii: bool = True,
    ) -> OutputGuardrailReport:
        """Execute output guardrail suite against the generated text."""
        start_time = time.monotonic()
        detectors_run: list[str] = []
        report = OutputGuardrailReport()
        active_domain = domain or self.default_domain

        # -------------------------------------------------------------
        # Stage 1: Schema Validation (Structural Guardrail)
        # -------------------------------------------------------------
        if expected_schema is not None:
            detectors_run.append("schema_validation")
            schema_res = self.schema_validator.validate(output_text, expected_schema)
            report.schema_validation = schema_res
            if not schema_res.passed:
                report.allowed = False
                report.block_reason = f"Schema validation failed: {'; '.join(schema_res.errors[:3])}"
                report.detectors_run = detectors_run
                report.latency_ms = (time.monotonic() - start_time) * 1000
                return report

        # -------------------------------------------------------------
        # Stage 2: Groundedness & Hallucination Check
        # -------------------------------------------------------------
        if source_context:
            detectors_run.append("groundedness")
            text_for_grounding = output_text
            if (
                expected_schema is not None
                and report.schema_validation.passed
                and isinstance(report.schema_validation.parsed_json, dict)
            ):
                vals = [
                    str(v)
                    for v in report.schema_validation.parsed_json.values()
                    if isinstance(v, (str, int, float))
                ]
                if vals:
                    text_for_grounding = ". ".join(vals)

            ground_res = self.groundedness_checker.check(
                text_for_grounding,
                source_context=source_context,
                domain=active_domain,
            )
            report.groundedness = ground_res
            if not ground_res.passed and active_domain != "creative":
                report.allowed = False
                report.block_reason = (
                    f"Groundedness check failed: score={ground_res.score:.2f} "
                    f"below threshold={ground_res.domain_threshold:.2f} "
                    f"({len(ground_res.unsupported_claims)} unsupported claims)."
                )
                report.detectors_run = detectors_run
                report.latency_ms = (time.monotonic() - start_time) * 1000
                return report

        # -------------------------------------------------------------
        # Stage 3: Leak Scrubber (Canary & PII Leaks)
        # -------------------------------------------------------------
        detectors_run.append("leak_scrubber")
        _leaked, sanitized, reasons = self.leak_scrubber.scrub(output_text, redact_pii=redact_pii)
        report.pii_leak = self.leak_scrubber.scan_pii_leak(output_text)

        # A canary leak is a severe breach -> hard block
        canary_leak = any("Canary Leak" in r for r in reasons)
        if canary_leak:
            report.allowed = False
            report.block_reason = "Critical security alert: System canary token leakage detected."
            report.detectors_run = detectors_run
            report.latency_ms = (time.monotonic() - start_time) * 1000
            return report

        # If PII was leaked but sanitized cleanly, we allow the scrubbed response through
        report.allowed = True
        report.sanitized_output = sanitized
        report.detectors_run = detectors_run
        report.latency_ms = (time.monotonic() - start_time) * 1000
        return report
