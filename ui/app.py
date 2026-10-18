"""FastAPI Interactive Guardrails Demonstration Server.

Provides a live web test console with interactive toggles for guardrails,
latency breakdown, PII tokenization visualization, and audit logs.
Uses zero external frontend dependencies (native HTML5, CSS3, and Vanilla JS).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardrails.pipeline import TrustworthyAIGateway  # noqa: E402

app = FastAPI(
    title="Trustworthy AI Guardrails Console",
    description="Interactive evaluation and testing console for multi-stage LLM guardrails.",
    version="1.0.0",
)

gateway = TrustworthyAIGateway()


class GatewayRequest(BaseModel):
    user_input: str
    source_context: str | None = None
    domain: str = "general"
    mock_mode: bool = True
    simulated_model_output: str | None = None
    expected_schema: dict[str, Any] | None = None


class GatewayResponse(BaseModel):
    verdict: str
    original_input: str
    sanitized_input: str
    final_output: str
    total_latency_ms: float
    input_report: dict[str, Any]
    output_report: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/process", response_model=GatewayResponse)
def process_query(req: GatewayRequest) -> GatewayResponse:
    """Process a user prompt through the complete Trustworthy AI Gateway."""

    def mock_llm(prompt: str, system_prompt: str | None = None) -> str:
        if req.simulated_model_output:
            return req.simulated_model_output
        if req.source_context:
            return f"According to enterprise records: {req.source_context}"
        return f"Processed query safely: {prompt}"

    resp = gateway.process(
        user_input=req.user_input,
        llm_fn=mock_llm,
        source_context=req.source_context,
        expected_schema=req.expected_schema,
        domain=req.domain,  # type: ignore[arg-type]
    )

    return GatewayResponse(
        verdict=resp.verdict.value,
        original_input=resp.original_input,
        sanitized_input=resp.sanitized_input,
        final_output=resp.final_output,
        total_latency_ms=round(resp.total_latency_ms, 2),
        input_report=resp.input_report.model_dump(),
        output_report=resp.output_report.model_dump() if resp.output_report else None,
        metadata=resp.metadata,
    )


@app.get("/api/benchmark_summary")
def get_benchmark_summary() -> dict[str, Any]:
    """Return the latest evaluation summary JSON."""
    summary_path = REPO_ROOT / "eval" / "eval_summary.json"
    if summary_path.exists():
        import json
        with open(summary_path, encoding="utf-8") as f:
            return json.load(f)
    return {"status": "No benchmark run recorded yet."}


@app.get("/", response_class=HTMLResponse)
def get_ui() -> str:
    """Serve the single-page modern HTML5/CSS3 guardrail dashboard."""
    html_file = Path(__file__).parent / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Trustworthy AI Console</h1><p>UI template loading...</p>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ui.app:app", host="127.0.0.1", port=8000, reload=True)
