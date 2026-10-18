"""Output Leak Scrubber: Canary Token & Data Leakage Prevention."""

from __future__ import annotations

from guardrails.input.injection_detector import CanaryTokenManager
from guardrails.input.pii_detector import PIIDetector
from guardrails.models import PIIResult


class OutputLeakScrubber:
    """Scans and scrubs output text for canary token breaches and PII leakage."""

    def __init__(
        self,
        canary_manager: CanaryTokenManager | None = None,
        pii_detector: PIIDetector | None = None,
    ) -> None:
        self.canary_manager = canary_manager or CanaryTokenManager()
        self.pii_detector = pii_detector or PIIDetector(default_mode="redact")

    def check_canary_leak(self, output_text: str) -> str | None:
        """Check if any confidential system canary token is present in the output."""
        return self.canary_manager.check_leakage(output_text)

    def scan_pii_leak(self, output_text: str) -> PIIResult:
        """Detect any raw PII or secret keys generated into the output."""
        return self.pii_detector.detect(output_text)

    def scrub(
        self,
        output_text: str,
        redact_pii: bool = True,
    ) -> tuple[bool, str, list[str]]:
        """Scrub output text for leakages.

        Returns:
            Tuple of (leak_detected: bool, sanitized_text: str, leak_reasons: list[str])
        """
        reasons: list[str] = []

        # 1. Canary leak check (Critical failure - system prompt compromised)
        leaked_canary = self.check_canary_leak(output_text)
        if leaked_canary:
            reasons.append(f"System Prompt Canary Leak detected: '{leaked_canary}'")

        # 2. PII leak check
        pii_res = self.scan_pii_leak(output_text)
        sanitized = output_text
        if pii_res.pii_detected:
            entities = [f.entity_type for f in pii_res.findings]
            reasons.append(f"PII entities leaked in response: {entities}")
            if redact_pii:
                anonymized_res = self.pii_detector.anonymize(output_text, mode="redact")
                sanitized = anonymized_res.anonymized_text

        leak_detected = len(reasons) > 0
        return leak_detected, sanitized, reasons
