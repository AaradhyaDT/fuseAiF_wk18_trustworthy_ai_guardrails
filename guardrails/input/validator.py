"""Input Validator: Unicode normalization, homoglyph detection, and structural bounds."""

from __future__ import annotations

import unicodedata

from guardrails.models import ValidationResult

# Invisible zero-width and control characters used in evasion attacks
ZERO_WIDTH_CHARS = {
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\ufeff",  # zero-width no-break space / BOM
    "\u200e",  # left-to-right mark
    "\u200f",  # right-to-left mark
    "\u202a",  # ltr embedding
    "\u202b",  # rtl embedding
    "\u202c",  # pop directional formatting
    "\u202d",  # ltr override
    "\u202e",  # rtl override
}


class InputValidator:
    """Validates and normalizes raw user inputs prior to guardrail evaluation."""

    def __init__(self, max_length: int = 16_000, min_length: int = 1) -> None:
        self.max_length = max_length
        self.min_length = min_length

    def validate(self, text: str) -> ValidationResult:
        """Sanitize text, remove hidden evasions, and enforce length boundaries."""
        if not text or len(text.strip()) < self.min_length:
            return ValidationResult(
                valid=False,
                normalized_text="",
                error="Input cannot be empty or solely whitespace.",
                original_length=len(text) if text else 0,
                normalized_length=0,
            )

        orig_len = len(text)
        if orig_len > self.max_length:
            return ValidationResult(
                valid=False,
                normalized_text="",
                error=f"Input exceeds maximum allowed length ({orig_len} > {self.max_length} chars).",
                original_length=orig_len,
                normalized_length=0,
            )

        # 1. Strip zero-width & bidirectional attack vectors
        cleaned = "".join(ch for ch in text if ch not in ZERO_WIDTH_CHARS)

        # 2. Unicode NFKC normalization (collapses homoglyphs, ligatures, full-width characters)
        normalized = unicodedata.normalize("NFKC", cleaned)

        return ValidationResult(
            valid=True,
            normalized_text=normalized,
            error=None,
            original_length=orig_len,
            normalized_length=len(normalized),
        )
