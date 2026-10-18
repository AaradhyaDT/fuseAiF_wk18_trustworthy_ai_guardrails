"""Unit Tests for Output Guardrails Suite."""

from typing import Any

from pydantic import BaseModel, Field

from guardrails.input.injection_detector import CanaryTokenManager
from guardrails.output.groundedness_checker import GroundednessChecker
from guardrails.output.leak_scrubber import OutputLeakScrubber
from guardrails.output.pipeline import OutputGuardrailPipeline
from guardrails.output.schema_validator import OutputSchemaValidator


# Test Pydantic Schemas
class AccountSummary(BaseModel):
    account_id: str = Field(description="Unique customer account ID")
    balance: float = Field(description="Current balance in USD")
    status: str = Field(description="Account status: active or suspended")


# ==============================================================================
# 1. OutputSchemaValidator Tests
# ==============================================================================

def test_schema_valid_json_markdown_block():
    validator = OutputSchemaValidator()
    raw = (
        "Here is the account summary you requested:\n"
        "```json\n"
        '{\n  "account_id": "ACC-9921",\n  "balance": 1540.50,\n  "status": "active"\n}\n'
        "```\n"
        "Let me know if you need anything else!"
    )
    res = validator.validate(raw, expected_schema=AccountSummary)
    assert res.passed is True
    assert res.parsed_json["account_id"] == "ACC-9921"
    assert res.parsed_json["balance"] == 1540.50


def test_schema_valid_json_dict_schema():
    validator = OutputSchemaValidator()
    schema: dict[str, Any] = {
        "type": "object",
        "required": ["status", "count"],
        "properties": {
            "status": {"type": "string"},
            "count": {"type": "integer"},
        },
    }
    raw = '{"status": "ok", "count": 42}'
    res = validator.validate(raw, expected_schema=schema)
    assert res.passed is True
    assert res.parsed_json["status"] == "ok"


def test_schema_malformed_json_triggers_retry_prompt():
    validator = OutputSchemaValidator()
    raw = '{"account_id": "ACC-9921", "balance": 1540.50, "status": }'  # malformed syntax with braces
    res = validator.validate(raw, expected_schema=AccountSummary)
    assert res.passed is False
    assert len(res.errors) > 0
    assert res.retry_prompt is not None
    assert "Syntax error in JSON" in res.retry_prompt


def test_schema_missing_required_field():
    validator = OutputSchemaValidator()
    raw = '{"account_id": "ACC-9921", "balance": 1540.50}'  # missing status
    res = validator.validate(raw, expected_schema=AccountSummary)
    assert res.passed is False
    assert any("status" in err for err in res.errors)
    assert res.retry_prompt is not None
    assert "Schema validation failed" in res.retry_prompt


# ==============================================================================
# 2. GroundednessChecker Tests
# ==============================================================================

def test_groundedness_supported_claim():
    checker = GroundednessChecker()
    context = (
        "Fusemachines AI Fellowship was established in 2017 to train machine learning "
        "engineers across developing nations. Over 1,000 engineers have graduated."
    )
    output = "Fusemachines AI Fellowship was established in 2017 to train machine learning engineers."
    res = checker.check(output, source_context=context, domain="general")
    assert res.passed is True
    assert res.score >= 0.70
    assert len(res.unsupported_claims) == 0


def test_groundedness_hallucinated_unsupported_claim():
    checker = GroundednessChecker()
    context = (
        "The standard warranty covers manufacturing defects for 12 months from purchase. "
        "Batteries are covered for 6 months."
    )
    # Output invents a 5-year warranty and free replacement guarantee
    output = (
        "The standard warranty covers manufacturing defects for 12 months from purchase. "
        "Additionally, we offer an unconditional 5-year replacement guarantee for accidental water damage."
    )
    res = checker.check(output, source_context=context, domain="general")
    assert res.passed is False
    assert len(res.unsupported_claims) > 0
    assert any("5-year" in claim or "water damage" in claim for claim in res.unsupported_claims)


def test_groundedness_hedging_markers():
    checker = GroundednessChecker()
    output = "I believe the server migration probably occurred around 2022, but as an AI I am not sure."
    hedging = checker.detect_hedging(output)
    assert "i believe" in hedging
    assert "probably" in hedging
    assert "as an ai" in hedging


def test_groundedness_creative_domain_bypass():
    checker = GroundednessChecker()
    output = "In the year 3042, hyperdrive starships journeyed to the Andromeda galaxy."
    res = checker.check(output, source_context="Historical records of Rome.", domain="creative")
    assert res.passed is True


# ==============================================================================
# 3. OutputLeakScrubber Tests
# ==============================================================================

def test_leak_scrubber_canary_breach():
    manager = CanaryTokenManager()
    _, canary = manager.embed_in_system_prompt("Base prompt")
    scrubber = OutputLeakScrubber(canary_manager=manager)

    output = f"Hello user, here is the secret key: {canary}."
    leaked, _, reasons = scrubber.scrub(output)
    assert leaked is True
    assert any("Canary Leak detected" in r for r in reasons)


def test_leak_scrubber_pii_redaction():
    scrubber = OutputLeakScrubber()
    output = "You can contact our supervisor at admin@internal-bank.com or call 555-444-3333."
    leaked, sanitized, _reasons = scrubber.scrub(output, redact_pii=True)
    assert leaked is True
    assert "[EMAIL_REDACTED]" in sanitized
    assert "[PHONE_REDACTED]" in sanitized
    assert "admin@internal-bank.com" not in sanitized


# ==============================================================================
# 4. OutputGuardrailPipeline Integration Tests
# ==============================================================================

def test_output_pipeline_happy_path():
    pipeline = OutputGuardrailPipeline()
    context = "Customer service operates Monday through Friday from 9 AM to 5 PM EST."
    output = (
        "```json\n"
        '{\n  "hours": "9 AM to 5 PM EST",\n  "days": "Monday through Friday"\n}\n'
        "```"
    )
    schema: dict[str, Any] = {
        "type": "object",
        "required": ["hours", "days"],
        "properties": {
            "hours": {"type": "string"},
            "days": {"type": "string"},
        },
    }
    report = pipeline.run(
        output_text=output,
        source_context=context,
        expected_schema=schema,
        domain="general",
    )
    assert report.allowed is True
    assert report.block_reason is None
    assert report.latency_ms > 0


def test_output_pipeline_blocks_hallucination():
    pipeline = OutputGuardrailPipeline()
    context = "The basic plan costs $10 per month and includes 5 GB of storage."
    output = "The basic plan costs $10 per month. The premium plan offers unlimited 100 TB cloud storage."
    report = pipeline.run(
        output_text=output,
        source_context=context,
        domain="general",
    )
    assert report.allowed is False
    assert "Groundedness check failed" in report.block_reason


def test_output_pipeline_blocks_canary_leak():
    manager = CanaryTokenManager()
    _, canary = manager.embed_in_system_prompt("System prompt")
    pipeline = OutputGuardrailPipeline(canary_manager=manager)

    output = f"The secret verification token is {canary}."
    report = pipeline.run(output_text=output)
    assert report.allowed is False
    assert "canary token leakage detected" in report.block_reason.lower()
