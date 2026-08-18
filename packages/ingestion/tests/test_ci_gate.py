from __future__ import annotations

from contextiq_ingestion.evaluation.ci_gate import evaluate_gate, render_markdown_report


THRESHOLDS = {
    "floors": {
        "context_recall": 0.85,
        "faithfulness": 0.9,
        "refusal_accuracy": 0.9,
    },
    "max_regression": {
        "context_recall": 0.03,
        "faithfulness": 0.02,
        "refusal_accuracy": 0.05,
    },
    "primary_metrics": ["faithfulness", "context_recall", "refusal_accuracy"],
}


def test_gate_pass_within_threshold():
    baseline = {
        "metrics": {
            "faithfulness": 0.94,
            "context_recall": 0.90,
            "refusal_accuracy": 1.0,
        }
    }
    current = {
        "metrics": {
            "faithfulness": 0.938,
            "context_recall": 0.89,
            "refusal_accuracy": 1.0,
        },
        "queries_evaluated": 75,
    }
    gate = evaluate_gate(current=current, baseline=baseline, thresholds=THRESHOLDS)
    assert gate["passed"] is True
    md = render_markdown_report(gate, pr_label="PR #17", baseline_label="main")
    assert "PASS" in md
    assert "Faithfulness" in md


def test_gate_fail_absolute_floor():
    baseline = {
        "metrics": {
            "faithfulness": 0.94,
            "context_recall": 0.90,
            "refusal_accuracy": 1.0,
        }
    }
    current = {
        "metrics": {
            "faithfulness": 0.95,
            "context_recall": 0.77,  # below 0.85 floor
            "refusal_accuracy": 1.0,
        }
    }
    gate = evaluate_gate(current=current, baseline=baseline, thresholds=THRESHOLDS)
    assert gate["passed"] is False
    recall = next(c for c in gate["checks"] if c["name"] == "context_recall")
    assert recall["passed"] is False
    md = render_markdown_report(gate)
    assert "FAIL" in md
    assert "Merge blocked" in md


def test_gate_fail_regression():
    baseline = {
        "metrics": {
            "faithfulness": 0.96,
            "context_recall": 0.92,
            "refusal_accuracy": 1.0,
        }
    }
    current = {
        "metrics": {
            "faithfulness": 0.90,  # -6% > max 2%
            "context_recall": 0.91,
            "refusal_accuracy": 1.0,
        }
    }
    gate = evaluate_gate(current=current, baseline=baseline, thresholds=THRESHOLDS)
    assert gate["passed"] is False
    faith = next(c for c in gate["checks"] if c["name"] == "faithfulness")
    assert faith["passed"] is False
