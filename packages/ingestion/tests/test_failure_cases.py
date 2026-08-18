from __future__ import annotations

from contextiq_ingestion.evaluation.failures import load_failure_cases


def test_load_failure_cases():
    data = load_failure_cases()
    assert data.get("case_count", 0) >= 5
    assert data.get("mitigated_count", 0) >= 1
    assert data.get("open_count", 0) >= 1
    ids = {c["id"] for c in data["cases"]}
    assert "F01" in ids and "F05" in ids
    for case in data["cases"]:
        impact = case.get("metric_impact") or {}
        assert "before" in impact and "after" in impact
        assert impact.get("source"), f"{case['id']} missing metric source"
