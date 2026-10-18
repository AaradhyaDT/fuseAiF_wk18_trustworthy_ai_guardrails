"""Core Data Contracts & Pydantic Models for Guardrail Pipelines."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class GuardrailVerdict(str, Enum):
    """Execution verdict for guardrail stages."""
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    FALLBACK = "FALLBACK"
    SAFE_RESPONSE = "SAFE_RESPONSE"


# ==============================================================================
# Input Guardrail Models
# ==============================================================================

class ValidationResult(BaseModel):
    """Result of structural input sanitation & normalization."""
    valid: bool = True
    normalized_text: str = ""
    error: str | None = None
    original_length: int = 0
    normalized_length: int = 0


class PIIFinding(BaseModel):
    """Individual PII entity detected in text."""
    entity_type: str
    text: str
    start: int
    end: int
    confidence: float = 1.0


class PIIResult(BaseModel):
    """Aggregate result from PII scanning."""
    pii_detected: bool = False
    findings: list[PIIFinding] = Field(default_factory=list)
    anonymized_text: str = ""
    vault_tokens: dict[str, str] = Field(default_factory=dict)


class InjectionCategory(str, Enum):
    """Categorization of prompt injection attacks."""
    DIRECT_INJECTION = "direct_injection"
    JAILBREAK = "jailbreak"
    EXTRACTION = "extraction"
    IMPERSONATION = "impersonation"
    CONTEXT_MANIPULATION = "context_manipulation"
    CANARY_LEAK = "canary_leak"
    NONE = "none"


class InjectionFinding(BaseModel):
    """Detected prompt injection signature."""
    category: str
    pattern_name: str
    matched_text: str
    risk_score: float = 1.0


class InjectionResult(BaseModel):
    """Aggregate result from prompt injection scanning."""
    is_injection: bool = False
    category: str = "none"
    risk_score: float = 0.0
    findings: list[InjectionFinding] = Field(default_factory=list)


class SensitiveCategory(str, Enum):
    """Taxonomy of sensitive / policy-violating topics."""
    WEAPONS_CBRN = "weapons_cbrn"
    CYBERWEAPONS_MALWARE = "cyberweapons_malware"
    SELF_HARM_CRISIS = "self_harm_crisis"
    EXTREMISM = "extremism"
    HATE_SPEECH = "hate_speech"
    FRAUD = "fraud"
    NONE = "none"


class SensitiveTopicFinding(BaseModel):
    """Matched sensitive topic occurrence."""
    category: str
    matched_term: str
    route_action: Literal["hard_block", "safe_response"] = "hard_block"
    confidence: float = 1.0


class SensitiveTopicResult(BaseModel):
    """Aggregate result from sensitive topic classification."""
    topics_detected: bool = False
    findings: list[SensitiveTopicFinding] = Field(default_factory=list)
    strictest_action: Literal["allowed", "safe_response", "hard_block"] = "allowed"
    crisis_response_needed: bool = False


class InputGuardrailReport(BaseModel):
    """Consolidated report for the Input Guardrail pipeline."""
    allowed: bool = True
    block_reason: str | None = None
    sanitized_text: str = ""
    validation: ValidationResult = Field(default_factory=ValidationResult)
    injection: InjectionResult = Field(default_factory=InjectionResult)
    pii: PIIResult = Field(default_factory=PIIResult)
    sensitive_topics: SensitiveTopicResult = Field(default_factory=SensitiveTopicResult)
    detectors_run: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0


# ==============================================================================
# Output Guardrail Models
# ==============================================================================

class SchemaValidationResult(BaseModel):
    """Result of structural schema conformance verification."""
    passed: bool = True
    errors: list[str] = Field(default_factory=list)
    parsed_json: dict[str, Any] | list[Any] | None = None
    retry_prompt: str | None = None


class GroundednessResult(BaseModel):
    """Factual groundedness and hallucination evaluation."""
    passed: bool = True
    score: float = 1.0
    domain_threshold: float = 0.70
    claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    hedging_markers: list[str] = Field(default_factory=list)


class OutputGuardrailReport(BaseModel):
    """Consolidated report for the Output Guardrail pipeline."""
    allowed: bool = True
    block_reason: str | None = None
    sanitized_output: str = ""
    schema_validation: SchemaValidationResult = Field(default_factory=SchemaValidationResult)
    groundedness: GroundednessResult = Field(default_factory=GroundednessResult)
    pii_leak: PIIResult = Field(default_factory=PIIResult)
    detectors_run: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0


# ==============================================================================
# Pipeline Final Response
# ==============================================================================

class PipelineResponse(BaseModel):
    """End-to-end response returned to application callers."""
    verdict: GuardrailVerdict
    original_input: str
    sanitized_input: str
    final_output: str
    input_report: InputGuardrailReport
    output_report: OutputGuardrailReport | None = None
    total_latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
