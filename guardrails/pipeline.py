"""Trustworthy AI Gateway: End-to-End Multi-Stage Orchestrator.

Unifies Input Guardrails, Generative Model Execution, Output Guardrails,
Reversible Tokenization Vault, and Fallback Circuit Breaker into a production gateway.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from guardrails.input.pii_detector import TokenizationVault
from guardrails.input.pipeline import InputGuardrailPipeline
from guardrails.input.sensitive_topic_classifier import SensitiveTopicClassifier
from guardrails.models import (
    GuardrailVerdict,
    PipelineResponse,
)
from guardrails.output.groundedness_checker import DomainType
from guardrails.output.pipeline import OutputGuardrailPipeline


class TrustworthyAIGateway:
    """Production-grade Trust & Safety Gateway for generative AI applications."""

    DEFAULT_FALLBACK_MESSAGE = (
        "We are currently unable to process your request in the requested format. "
        "A representative will review your inquiry shortly."
    )

    def __init__(
        self,
        input_pipeline: InputGuardrailPipeline | None = None,
        output_pipeline: OutputGuardrailPipeline | None = None,
        max_regeneration_attempts: int = 1,
    ) -> None:
        self.input_pipeline = input_pipeline or InputGuardrailPipeline()
        self.output_pipeline = output_pipeline or OutputGuardrailPipeline(
            canary_manager=self.input_pipeline.canary_manager
        )
        self.max_regeneration_attempts = max_regeneration_attempts

    def process(
        self,
        user_input: str,
        llm_fn: Callable[[str, str | None], str],
        source_context: str | None = None,
        expected_schema: dict[str, Any] | type[BaseModel] | None = None,
        domain: DomainType = "general",
        system_prompt: str | None = None,
        enable_canary: bool = True,
    ) -> PipelineResponse:
        """Process a user request end-to-end through input and output guardrails.

        Args:
            user_input: Raw query submitted by the user.
            llm_fn: Callable `(prompt: str, system_prompt: str | None) -> str` invoking the LLM.
            source_context: Grounding context (e.g. retrieved RAG chunks) for factual verification.
            expected_schema: Pydantic model or JSON Schema dict for structured output.
            domain: Target domain ('general', 'medical', 'financial', etc.) for groundedness threshold.
            system_prompt: Base system prompt for the application.
            enable_canary: Embed confidential canary token in system prompt.

        Returns:
            PipelineResponse containing execution verdict, sanitized text, and diagnostic reports.
        """
        start_time = time.monotonic()
        vault = TokenizationVault()

        # =============================================================
        # 1. Pre-Execution Input Guardrail Pipeline
        # =============================================================
        input_report = self.input_pipeline.run(user_input, vault=vault)

        # Handle input rejection
        if not input_report.allowed:
            total_time = (time.monotonic() - start_time) * 1000
            return PipelineResponse(
                verdict=GuardrailVerdict.BLOCKED,
                original_input=user_input,
                sanitized_input=user_input,
                final_output=f"Request blocked by safety policy: {input_report.block_reason}",
                input_report=input_report,
                output_report=None,
                total_latency_ms=total_time,
                metadata={"block_stage": "input"},
            )

        # Handle crisis intervention routing
        if input_report.sensitive_topics.crisis_response_needed:
            total_time = (time.monotonic() - start_time) * 1000
            return PipelineResponse(
                verdict=GuardrailVerdict.SAFE_RESPONSE,
                original_input=user_input,
                sanitized_input=input_report.sanitized_text,
                final_output=SensitiveTopicClassifier.CRISIS_HELPLINE_MESSAGE,
                input_report=input_report,
                output_report=None,
                total_latency_ms=total_time,
                metadata={"route": "crisis_helpline"},
            )

        # =============================================================
        # 2. Embed Canary Token & Invoke Model
        # =============================================================
        effective_system_prompt = system_prompt or "You are a helpful and trustworthy assistant."
        if enable_canary:
            effective_system_prompt, _ = self.input_pipeline.canary_manager.embed_in_system_prompt(
                effective_system_prompt
            )

        sanitized_input = input_report.sanitized_text

        # Call downstream generative model
        raw_output = llm_fn(sanitized_input, effective_system_prompt)

        # =============================================================
        # 3. Post-Execution Output Guardrail Pipeline (with 1-Pass Retry)
        # =============================================================
        output_report = self.output_pipeline.run(
            output_text=raw_output,
            source_context=source_context,
            expected_schema=expected_schema,
            domain=domain,
        )

        # -------------------------------------------------------------
        # Corrective Retry Loop (if Schema Validation Failed)
        # -------------------------------------------------------------
        attempts_left = self.max_regeneration_attempts
        while (
            not output_report.allowed
            and not output_report.schema_validation.passed
            and output_report.schema_validation.retry_prompt
            and attempts_left > 0
        ):
            attempts_left -= 1
            # Re-prompt model with specific corrective feedback
            corrective_prompt = (
                f"{sanitized_input}\n\n"
                f"[SYSTEM INSTRUCTION]: {output_report.schema_validation.retry_prompt}"
            )
            raw_output = llm_fn(corrective_prompt, effective_system_prompt)
            output_report = self.output_pipeline.run(
                output_text=raw_output,
                source_context=source_context,
                expected_schema=expected_schema,
                domain=domain,
            )

        # =============================================================
        # 4. Fallback Circuit Breaker
        # =============================================================
        if not output_report.allowed:
            total_time = (time.monotonic() - start_time) * 1000
            return PipelineResponse(
                verdict=GuardrailVerdict.FALLBACK,
                original_input=user_input,
                sanitized_input=sanitized_input,
                final_output=self.DEFAULT_FALLBACK_MESSAGE,
                input_report=input_report,
                output_report=output_report,
                total_latency_ms=total_time,
                metadata={"fallback_reason": output_report.block_reason},
            )

        # =============================================================
        # 5. Reverse Detokenization (Restore PII for User Visibility)
        # =============================================================
        final_text = vault.detokenize(output_report.sanitized_output or raw_output)

        total_time = (time.monotonic() - start_time) * 1000
        return PipelineResponse(
            verdict=GuardrailVerdict.ALLOWED,
            original_input=user_input,
            sanitized_input=sanitized_input,
            final_output=final_text,
            input_report=input_report,
            output_report=output_report,
            total_latency_ms=total_time,
            metadata={"attempts_used": self.max_regeneration_attempts - attempts_left},
        )
