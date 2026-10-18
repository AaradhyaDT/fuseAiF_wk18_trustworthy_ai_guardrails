"""Input Guardrails Pipeline: Unified Pre-LLM Orchestration."""

from __future__ import annotations

import time

from guardrails.input.injection_detector import CanaryTokenManager, InjectionDetector
from guardrails.input.pii_detector import PIIDetector, TokenizationVault
from guardrails.input.sensitive_topic_classifier import SensitiveTopicClassifier
from guardrails.input.validator import InputValidator
from guardrails.models import InputGuardrailReport


class InputGuardrailPipeline:
    """Orchestrates input guardrail stages sequentially in cheapest-first order.

    Stages:
    1. Input Validation: Normalization, zero-width stripping, length limits.
    2. Prompt Injection Detection: Fast pattern & heuristic scan.
    3. PII Detection & Anonymization: Reversible vault tokenization.
    4. Sensitive Topic Classification: Hard block vs safe crisis routing.
    """

    def __init__(
        self,
        max_input_length: int = 16_000,
        anonymize_pii: bool = True,
        pii_mode: str = "tokenize",
    ) -> None:
        self.validator = InputValidator(max_length=max_input_length)
        self.injection_detector = InjectionDetector()
        self.pii_detector = PIIDetector(default_mode=pii_mode)  # type: ignore[arg-type]
        self.sensitive_classifier = SensitiveTopicClassifier()
        self.canary_manager = CanaryTokenManager()
        self.anonymize_pii = anonymize_pii

    def run(
        self,
        text: str,
        vault: TokenizationVault | None = None,
    ) -> InputGuardrailReport:
        """Execute full input guardrail suite against the provided prompt."""
        start_time = time.monotonic()
        detectors_run: list[str] = []
        report = InputGuardrailReport()

        # -------------------------------------------------------------
        # Stage 1: Input Validation & Normalization
        # -------------------------------------------------------------
        detectors_run.append("validation")
        val_result = self.validator.validate(text)
        report.validation = val_result
        if not val_result.valid:
            report.allowed = False
            report.block_reason = val_result.error or "Input validation failed."
            report.detectors_run = detectors_run
            report.latency_ms = (time.monotonic() - start_time) * 1000
            return report

        safe_text = val_result.normalized_text

        # -------------------------------------------------------------
        # Stage 2: Prompt Injection Detection (Fail-Closed)
        # -------------------------------------------------------------
        detectors_run.append("injection")
        inj_result = self.injection_detector.scan(safe_text)
        report.injection = inj_result
        if inj_result.is_injection:
            report.allowed = False
            report.block_reason = (
                f"Prompt injection violation detected [{inj_result.category}]. "
                f"Risk score: {inj_result.risk_score:.2f}."
            )
            report.detectors_run = detectors_run
            report.latency_ms = (time.monotonic() - start_time) * 1000
            return report

        # -------------------------------------------------------------
        # Stage 3: PII Scanning & Reversible Tokenization
        # -------------------------------------------------------------
        detectors_run.append("pii")
        if self.anonymize_pii:
            pii_result = self.pii_detector.anonymize(safe_text, vault=vault)
            safe_text = pii_result.anonymized_text
        else:
            pii_result = self.pii_detector.detect(safe_text)
        report.pii = pii_result

        # -------------------------------------------------------------
        # Stage 4: Sensitive Topic Classification
        # -------------------------------------------------------------
        detectors_run.append("sensitive_topics")
        topic_result = self.sensitive_classifier.classify(safe_text)
        report.sensitive_topics = topic_result

        if topic_result.topics_detected:
            if topic_result.strictest_action == "hard_block":
                report.allowed = False
                cats = [f.category for f in topic_result.findings]
                report.block_reason = f"Prohibited sensitive content detected: {list(set(cats))}."
                report.detectors_run = detectors_run
                report.latency_ms = (time.monotonic() - start_time) * 1000
                return report
            elif topic_result.crisis_response_needed:
                # Crisis is allowed through but flagged for dedicated supportive routing
                report.block_reason = "Crisis content flagged: safe helpline response required."

        # All input stages passed
        report.allowed = True
        report.sanitized_text = safe_text
        report.detectors_run = detectors_run
        report.latency_ms = (time.monotonic() - start_time) * 1000
        return report
