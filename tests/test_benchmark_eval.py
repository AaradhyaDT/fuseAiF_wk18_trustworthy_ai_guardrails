"""Test Suite for 26-case Golden Benchmark Evaluation Pipeline."""

from __future__ import annotations

from eval.run_eval import load_benchmark, run_benchmark


def test_golden_benchmark_structure_and_coverage():
    """Verify golden benchmark exists, has >= 20 cases, and covers required categories."""
    cases = load_benchmark()
    assert len(cases) >= 20, f"Expected at least 20 test cases, found {len(cases)}"

    categories = {c["category"] for c in cases}
    required_categories = {
        "benign_inquiry",
        "pii_sanitization",
        "adversarial_instruction",
        "policy_safety",
        "factual_consistency",
        "structural_schema",
    }
    assert required_categories.issubset(categories), f"Missing categories: {required_categories - categories}"


def test_benchmark_runner_execution_and_metrics():
    """Verify run_benchmark executes without runtime regressions and achieves high accuracy."""
    cases = load_benchmark()
    results, metrics = run_benchmark(cases)

    assert len(results) == len(cases)
    assert metrics["dataset_total"] >= 20
    assert metrics["overall_accuracy"] >= 0.90, f"Benchmark accuracy dropped to {metrics['overall_accuracy']}"
    assert metrics["threat_detection_matrix"]["precision"] >= 0.90
    assert metrics["latency_profile_ms"]["mean"] < 50.0  # Ultra-fast CPU latency
