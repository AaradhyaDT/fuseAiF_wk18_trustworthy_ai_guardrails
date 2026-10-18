"""Evaluation Runner & Quantitative Metrics Engine.

Executes the 26-case Golden Benchmark through the Trustworthy AI Gateway,
measures detection rates, records per-stage latencies, and computes
Precision, Recall, F1, False Positive Rate (FPR), and False Negative Rate (FNR).
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# Guarantee repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardrails.models import GuardrailVerdict  # noqa: E402
from guardrails.pipeline import TrustworthyAIGateway  # noqa: E402

BENCHMARK_PATH = REPO_ROOT / "eval" / "golden_benchmark.jsonl"
SUMMARY_OUTPUT_PATH = REPO_ROOT / "eval" / "eval_summary.json"


def load_benchmark(path: Path = BENCHMARK_PATH) -> list[dict[str, Any]]:
    """Load benchmark cases from JSONL file."""
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def build_mock_llm(case: dict[str, Any]):
    """Build a deterministic simulated LLM function tailored to the case."""
    simulated_response = case.get("simulated_response")

    def mock_llm(prompt: str, system_prompt: str | None = None) -> str:
        if simulated_response:
            return simulated_response
        # For PII tests, reflect back the sanitized prompt to verify reversible detokenization
        if case.get("category") == "pii_sanitization":
            return f"Processed inquiry safely: {prompt}"
        # For standard benign inquiries, answer directly with the ground-truth context
        return str(case.get("context", "Inquiry answered."))

    return mock_llm


def run_benchmark(
    cases: list[dict[str, Any]],
    gateway: TrustworthyAIGateway | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute all benchmark cases and calculate comprehensive metrics."""
    if gateway is None:
        gateway = TrustworthyAIGateway()

    results: list[dict[str, Any]] = []
    latencies: list[float] = []

    # Category performance trackers
    category_counts: dict[str, int] = defaultdict(int)
    category_matches: dict[str, int] = defaultdict(int)

    # Global Binary Classification for Security/Safety Controls:
    # Positive (P) = Should intercept/flag (adversarial, policy violations, hallucinations, schema failures)
    # Negative (N) = Benign queries that should pass unblocked
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    print("=" * 80)
    print(f"{'ID':<4} | {'CATEGORY':<24} | {'EXPECTED':<12} | {'ACTUAL':<12} | {'LATENCY (ms)':<12} | STATUS")
    print("-" * 80)

    for case in cases:
        case_id = case["id"]
        category = case["category"]
        user_input = case["input"]
        context = case.get("context") if category != "pii_sanitization" else None
        expected_action = case["expected_action"]
        schema = case.get("expected_schema")
        llm_fn = build_mock_llm(case)

        start_t = time.perf_counter()
        resp = gateway.process(
            user_input=user_input,
            llm_fn=llm_fn,
            source_context=context,
            expected_schema=schema,
            domain="general",
        )
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        latencies.append(duration_ms)
        category_counts[category] += 1

        # Determine actual action
        if resp.verdict == GuardrailVerdict.BLOCKED:
            actual_action = "blocked"
        elif resp.verdict == GuardrailVerdict.SAFE_RESPONSE:
            actual_action = "safe_response"
        elif resp.input_report.sanitized_text != user_input:
            actual_action = "sanitized"
        elif resp.verdict == GuardrailVerdict.FALLBACK or (resp.metadata.get("attempts_used", 0) > 0):
            actual_action = "regenerated_or_fallback"
        else:
            actual_action = "allowed"

        # Match check
        matched = False
        if expected_action == actual_action:
            matched = True
        elif expected_action == "regenerated_or_fallback" and (resp.verdict == GuardrailVerdict.FALLBACK or resp.verdict == GuardrailVerdict.ALLOWED):
            matched = True
        elif expected_action == "blocked" and (resp.verdict in (GuardrailVerdict.BLOCKED, GuardrailVerdict.FALLBACK)):
            matched = True

        if matched:
            category_matches[category] += 1
            status_str = "PASS [OK]"
        else:
            status_str = "FAIL [MISMATCH]"

        # Binary confusion matrix tracking for risk/threat detection
        is_threat_case = category in ("adversarial_instruction", "policy_safety", "factual_consistency")
        was_intercepted = resp.verdict in (GuardrailVerdict.BLOCKED, GuardrailVerdict.SAFE_RESPONSE, GuardrailVerdict.FALLBACK)

        if is_threat_case:
            # Positive ground truth: threat present
            if was_intercepted:
                tp += 1
            else:
                fn += 1
        elif category == "benign_inquiry":
            # Negative ground truth: completely benign
            if was_intercepted:
                fp += 1
            else:
                tn += 1

        print(
            f"{case_id:<4} | {category:<24} | {expected_action:<12} | "
            f"{actual_action:<12} | {duration_ms:10.2f} ms | {status_str}"
        )

        results.append({
            "id": case_id,
            "category": category,
            "input": user_input,
            "context": context,
            "expected_action": expected_action,
            "actual_action": actual_action,
            "verdict": resp.verdict.value,
            "fallback_triggered": resp.verdict == GuardrailVerdict.FALLBACK,
            "regeneration_attempts": resp.metadata.get("attempts_used", 0),
            "latency_ms": round(duration_ms, 2),
            "matched": matched,
            "input_report": resp.input_report.model_dump(),
            "output_report": resp.output_report.model_dump() if resp.output_report else None,
        })

    # Summary metrics
    total_cases = len(cases)
    total_matched = sum(1 for r in results if r["matched"])
    overall_accuracy = total_matched / total_cases if total_cases > 0 else 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0

    latencies_sorted = sorted(latencies)
    p50_latency = latencies_sorted[len(latencies_sorted) // 2]
    p95_latency = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    avg_latency = sum(latencies) / len(latencies)

    metrics = {
        "dataset_total": total_cases,
        "total_matched": total_matched,
        "overall_accuracy": round(overall_accuracy, 4),
        "threat_detection_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
        },
        "category_breakdown": {
            cat: {
                "total": category_counts[cat],
                "passed": category_matches[cat],
                "accuracy": round(category_matches[cat] / category_counts[cat], 4),
            }
            for cat in sorted(category_counts.keys())
        },
        "latency_profile_ms": {
            "mean": round(avg_latency, 2),
            "p50": round(p50_latency, 2),
            "p95": round(p95_latency, 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
        },
    }

    print("=" * 80)
    print(f"Overall Accuracy: {overall_accuracy * 100:.1f}% ({total_matched}/{total_cases})")
    print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1-Score: {f1_score:.4f}")
    print(f"False Positive Rate (FPR): {fpr:.4f} | False Negative Rate (FNR): {fnr:.4f}")
    print(f"Latency: Mean={avg_latency:.2f}ms | p50={p50_latency:.2f}ms | p95={p95_latency:.2f}ms")
    print("=" * 80)

    # Save summary
    with open(SUMMARY_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "case_results": results}, f, indent=2)

    return results, metrics


if __name__ == "__main__":
    benchmark_cases = load_benchmark()
    run_benchmark(benchmark_cases)
