"""PII Detector & Reversible Tokenization Vault.

Supports high-precision multi-entity detection (Email, Phone, SSN, Credit Cards, API Keys, IPs)
and handles adversarial obfuscations (e.g. spaced characters, bracketed '@', 'dot').
Provides a stateful TokenizationVault to de-anonymize data safely upon model return.
"""

from __future__ import annotations

import re
from typing import ClassVar, Literal

from guardrails.models import PIIFinding, PIIResult

AnonymizationMode = Literal["tokenize", "redact", "mask"]


def _luhn_checksum(card_number: str) -> bool:
    """Validate credit card number using the Luhn algorithm."""
    digits = [int(d) for d in re.sub(r"\D", "", card_number)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


class TokenizationVault:
    """Reversible in-memory mapping between sensitive PII values and synthetic tokens."""

    def __init__(self) -> None:
        self._raw_to_token: dict[str, str] = {}
        self._token_to_raw: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    def get_or_create_token(self, entity_type: str, raw_value: str) -> str:
        """Return existing surrogate token or allocate a new deterministic token."""
        clean_key = raw_value.strip().lower()
        if clean_key in self._raw_to_token:
            return self._raw_to_token[clean_key]

        count = self._counters.get(entity_type, 0) + 1
        self._counters[entity_type] = count
        token = f"<{entity_type}_{count}>"

        self._raw_to_token[clean_key] = token
        self._token_to_raw[token] = raw_value
        return token

    def detokenize(self, text: str) -> str:
        """Replace surrogate tokens in text with their original sensitive values."""
        result = text
        for token, raw_val in self._token_to_raw.items():
            result = result.replace(token, raw_val)
        return result

    @property
    def vault_mappings(self) -> dict[str, str]:
        """Return a copy of the token-to-raw mapping."""
        return dict(self._token_to_raw)


class PIIDetector:
    """Rule and regex engine for entity detection, obfuscation resolution, and anonymization."""

    # Core regex patterns for standard PII entities
    PATTERNS: ClassVar[list[tuple[str, re.Pattern, float]]] = [
        # Email Addresses
        ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), 1.0),
        # US / International Social Security Numbers
        ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 0.95),
        # Phone Numbers (International E.164, US standard, and 10-digit South Asian / Nepali)
        ("PHONE", re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), 0.90),
        ("PHONE_LOCAL", re.compile(r"\b(?:98\d{8}|97\d{8})\b"), 0.95),
        # API Keys & Sensitive Secrets (OpenAI, Stripe, GitHub, AWS, etc.)
        ("API_KEY", re.compile(r"\b(?:sk[-_](?:live|test)?[a-zA-Z0-9_-]{15,}|ghp_[a-zA-Z0-9]{30,}|AKIA[0-9A-Z]{16})\b"), 1.0),
        # IPv4 Addresses
        ("IP_ADDRESS", re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"), 0.85),
    ]

    # Obfuscated PII patterns (adversarial evasions)
    OBFUSCATION_PATTERNS: ClassVar[list[tuple[str, re.Pattern, float]]] = [
        ("EMAIL_AT_DOT", re.compile(r"\b[A-Za-z0-9._%+-]+\s*(?:\[at\]|\(at\)|\bat\b)\s*[A-Za-z0-9.-]+\s*(?:\[dot\]|\(dot\)|\bdot\b)\s*[A-Za-z]{2,}\b", re.IGNORECASE), 0.95),
        ("EMAIL_SPACED", re.compile(r"\b(?:[A-Za-z0-9]\s+){3,}@\s*(?:[A-Za-z0-9]\s+){2,}\.\s*[A-Za-z]{2,}\b"), 0.95),
        ("SSN_SPACED", re.compile(r"\b\d\s\d\s\d\s*-\s*\d\s\d\s*-\s*\d\s\d\s\d\s\d\b"), 0.95),
        ("PHONE_SPACED", re.compile(r"\(\s*\d\s*\d\s*\d\s*\)\s+\d\s*\d\s*\d\s*-\s*\d\s*\d\s*\d\s*\d\b"), 0.90),
    ]

    CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b")

    def __init__(self, default_mode: AnonymizationMode = "tokenize") -> None:
        self.default_mode = default_mode

    def detect(self, text: str) -> PIIResult:
        """Scan text and return structured PII findings."""
        findings: list[PIIFinding] = []
        seen_spans: set[tuple[int, int]] = set()

        # 1. Standard patterns
        for entity_type, pattern, conf in self.PATTERNS:
            for match in pattern.finditer(text):
                span = match.span()
                if not any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                    seen_spans.add(span)
                    findings.append(
                        PIIFinding(
                            entity_type=entity_type,
                            text=match.group(),
                            start=span[0],
                            end=span[1],
                            confidence=conf,
                        )
                    )

        # 2. Obfuscation patterns
        for entity_type, pattern, conf in self.OBFUSCATION_PATTERNS:
            for match in pattern.finditer(text):
                span = match.span()
                if not any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                    seen_spans.add(span)
                    findings.append(
                        PIIFinding(
                            entity_type=entity_type,
                            text=match.group(),
                            start=span[0],
                            end=span[1],
                            confidence=conf,
                        )
                    )

        # 3. Credit Card detection with Luhn verification
        for match in self.CREDIT_CARD_PATTERN.finditer(text):
            candidate = match.group()
            digits = re.sub(r"\D", "", candidate)
            if 13 <= len(digits) <= 19 and _luhn_checksum(digits):
                span = match.span()
                if not any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                    seen_spans.add(span)
                    findings.append(
                        PIIFinding(
                            entity_type="CREDIT_CARD",
                            text=candidate,
                            start=span[0],
                            end=span[1],
                            confidence=0.98,
                        )
                    )

        # Sort findings by start position ascending
        findings.sort(key=lambda f: f.start)
        return PIIResult(
            pii_detected=len(findings) > 0,
            findings=findings,
            anonymized_text=text,
        )

    def anonymize(
        self,
        text: str,
        mode: AnonymizationMode | None = None,
        vault: TokenizationVault | None = None,
    ) -> PIIResult:
        """Scan text and apply the chosen anonymization strategy."""
        result = self.detect(text)
        if not result.pii_detected:
            return result

        active_mode = mode or self.default_mode
        active_vault = vault if vault is not None else TokenizationVault()

        # Build replacement string from back to front to preserve offsets
        chars = list(text)
        for finding in sorted(result.findings, key=lambda f: f.start, reverse=True):
            raw = finding.text
            if active_mode == "tokenize":
                clean_type = finding.entity_type.split("_")[0]
                replacement = active_vault.get_or_create_token(clean_type, raw)
            elif active_mode == "redact":
                replacement = f"[{finding.entity_type}_REDACTED]"
            else:  # mask
                if len(raw) > 4:
                    replacement = raw[:2] + ("*" * (len(raw) - 4)) + raw[-2:]
                else:
                    replacement = "****"
            chars[finding.start:finding.end] = list(replacement)

        anonymized = "".join(chars)
        return PIIResult(
            pii_detected=True,
            findings=result.findings,
            anonymized_text=anonymized,
            vault_tokens=active_vault.vault_mappings,
        )
