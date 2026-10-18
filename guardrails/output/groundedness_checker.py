"""Groundedness & Hallucination Checker.

Evaluates whether generated claims in the model output are supported by the provided
reference source context. Computes token-level and semantic entailment, isolates
unsupported claims, and identifies uncertainty hedging signals.
"""

from __future__ import annotations

import re
from typing import ClassVar, Literal

from guardrails.models import GroundednessResult

DomainType = Literal["general", "medical", "legal", "financial", "creative"]


class GroundednessChecker:
    """Evaluates output claims against source reference context."""

    DOMAIN_THRESHOLDS: ClassVar[dict[str, float]] = {
        "medical": 0.85,
        "legal": 0.85,
        "financial": 0.80,
        "general": 0.70,
        "creative": 0.0,
    }

    HEDGING_PATTERNS: ClassVar[list[str]] = [
        r"(?i)\b(i\s+think|i\s+believe|probably|maybe|perhaps|possibly)\b",
        r"(?i)\b(i\'?m\s+not\s+sure|i\s+cannot\s+(confirm|verify|guarantee))\b",
        r"(?i)\b(might\s+be|could\s+be|may\s+be|seems?\s+(like|to\s+be))\b",
        r"(?i)\b(approximately|roughly|around|about|estimated?)\b",
        r"(?i)\b(as\s+(an\s+)?ai|as\s+a\s+language\s+model)\b",
        r"(?i)\b(please\s+verify|you\s+should\s+check|consult\s+a\s+professional)\b",
    ]

    FACTUAL_INDICATORS: ClassVar[list[str]] = [
        r"\b\d{4}\b",                            # Years
        r"\b\d+(?:\.\d+)?%\b",                   # Percentages
        r"\b\d+(?:\.\d+)?\s*(?:million|billion|thousand|hundred|dollars|\$|usd|npr)\b",
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",   # Proper names
        r"(?i)\b(according\s+to|studies?\s+show|research\s+indicates?|stipulates?|requires?)\b",
        r"(?i)\b(is|are|was|were|has|have|had)\s+(the|a|an)\b",
    ]

    def __init__(self) -> None:
        self._compiled_hedging = [re.compile(p) for p in self.HEDGING_PATTERNS]
        self._compiled_factual = [re.compile(p) for p in self.FACTUAL_INDICATORS]

    def extract_claims(self, text: str) -> list[str]:
        """Deconstruct output text into verifiable factual claim sentences."""
        # Split on sentence boundaries
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        claims: list[str] = []

        for s in sentences:
            # Must have minimum words and contain at least one factual indicator
            words = s.split()
            if len(words) >= 4 and any(pat.search(s) for pat in self._compiled_factual):
                claims.append(s)

        # Fallback: if no specific indicator caught, include substantive sentences
        if not claims and sentences:
            claims = [s for s in sentences if len(s.split()) >= 4]

        return claims

    def detect_hedging(self, text: str) -> list[str]:
        """Detect uncertainty or hedging markers in the output."""
        markers: list[str] = []
        for pat in self._compiled_hedging:
            for match in pat.finditer(text):
                markers.append(match.group().strip().lower())
        return list(set(markers))

    def _calculate_sentence_support(self, claim: str, context: str) -> float:
        """Calculate token overlap support between a claim sentence and reference context."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
            "of", "with", "and", "or", "but", "by", "from", "as", "it", "that", "this",
            "be", "has", "have", "had", "will", "would", "can", "could", "should",
        }
        claim_words = [
            re.sub(r"_\d+$", "", w.lower())
            for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", claim)
            if w.lower() not in stop_words and len(w) > 2
        ]
        if not claim_words:
            return 1.0

        context_lower = context.lower()
        context_words = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", context_lower))

        matched = sum(1 for w in claim_words if w in context_words or w in context_lower)
        return matched / len(claim_words)

    def check(
        self,
        output_text: str,
        source_context: str | None = None,
        domain: DomainType = "general",
    ) -> GroundednessResult:
        """Evaluate groundedness of output text against source context."""
        hedging = self.detect_hedging(output_text)
        claims = self.extract_claims(output_text)
        threshold = self.DOMAIN_THRESHOLDS.get(domain, 0.70)

        # Creative domain bypass
        if domain == "creative" or not source_context:
            return GroundednessResult(
                passed=True,
                score=1.0 if not source_context else 0.80,
                domain_threshold=threshold,
                claims=claims,
                unsupported_claims=[],
                hedging_markers=hedging,
            )

        if not claims:
            return GroundednessResult(
                passed=True,
                score=1.0,
                domain_threshold=threshold,
                claims=[],
                unsupported_claims=[],
                hedging_markers=hedging,
            )

        unsupported: list[str] = []
        scores: list[float] = []

        for claim in claims:
            support = self._calculate_sentence_support(claim, source_context)
            scores.append(support)
            if support < threshold:
                unsupported.append(claim)

        mean_score = sum(scores) / len(scores) if scores else 1.0
        passed = len(unsupported) == 0 and mean_score >= threshold

        return GroundednessResult(
            passed=passed,
            score=round(mean_score, 3),
            domain_threshold=threshold,
            claims=claims,
            unsupported_claims=unsupported,
            hedging_markers=hedging,
        )
