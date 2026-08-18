"""CI gate: compare PR metrics to baseline + absolute floors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contextiq_ingestion.config import repo_root

DEFAULT_THRESHOLDS = repo_root() / "eval" / "ci" / "thresholds.json"
DEFAULT_BASELINE = repo_root() / "eval" / "ci" / "baseline.json"
DEFAULT_CURRENT = repo_root() / "docs" / "eval-results" / "rag-metrics.json"


@dataclass
class MetricCheck:
    name: str
    baseline: float | None
    current: float | None
    delta: float | None
    floor: float | None
    max_drop: float | None
    passed: bool
    reason: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics_from(payload: dict[str, Any]) -> dict[str, float]:
    raw = payload.get("metrics") or {}
    out: dict[str, float] = {}
    for k, v in raw.items():
        if v is None:
            continue
        out[k] = float(v)
    return out


def evaluate_gate(
    *,
    current: dict[str, Any],
    baseline: dict[str, Any],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    cur_m = _metrics_from(current)
    base_m = _metrics_from(baseline)
    floors: dict[str, float] = {
        k: float(v) for k, v in (thresholds.get("floors") or {}).items()
    }
    max_reg: dict[str, float] = {
        k: float(v) for k, v in (thresholds.get("max_regression") or {}).items()
    }
    primary = list(
        thresholds.get("primary_metrics")
        or ["faithfulness", "context_recall", "refusal_accuracy"]
    )

    checks: list[MetricCheck] = []
    for name in primary:
        cur = cur_m.get(name)
        base = base_m.get(name)
        floor = floors.get(name)
        max_drop = max_reg.get(name)
        delta = None if cur is None or base is None else cur - base
        passed = True
        reasons: list[str] = []

        if cur is None:
            passed = False
            reasons.append("missing from current metrics")
        else:
            if floor is not None and cur < floor:
                passed = False
                reasons.append(f"below floor {floor:.1%} (actual {cur:.1%})")
            if (
                delta is not None
                and max_drop is not None
                and delta < -max_drop
            ):
                passed = False
                reasons.append(
                    f"regressed {delta:+.1%} vs baseline (max drop -{max_drop:.1%})"
                )

        if not reasons:
            reasons.append("within threshold")

        checks.append(
            MetricCheck(
                name=name,
                baseline=base,
                current=cur,
                delta=delta,
                floor=floor,
                max_drop=max_drop,
                passed=passed,
                reason="; ".join(reasons),
            )
        )

    overall = all(c.passed for c in checks)
    return {
        "passed": overall,
        "checks": [c.__dict__ for c in checks],
        "current_ref": {
            "queries_evaluated": current.get("queries_evaluated"),
            "strategy": current.get("strategy"),
            "mode": current.get("mode"),
            "generator": current.get("generator"),
        },
        "baseline_ref": baseline.get("ref") or "baseline",
    }


def render_markdown_report(
    gate: dict[str, Any],
    *,
    pr_label: str = "PR",
    baseline_label: str = "main",
) -> str:
    lines = [
        "## RAG Evaluation",
        "",
    ]
    if gate["passed"]:
        lines.append("**Result: ✓ PASS — within threshold**")
    else:
        lines.append("**Result: ❌ FAIL — evaluation gate blocked**")
    lines.append("")

    for c in gate["checks"]:
        name = c["name"].replace("_", " ").title()
        base = c["baseline"]
        cur = c["current"]
        delta = c["delta"]
        lines.extend(
            [
                f"### {name}",
                "",
                f"**{baseline_label}**",
                "",
                "────────────────",
                "",
                f"{_pct(base)}" if base is not None else "—",
                "",
                f"**{pr_label}**",
                "",
                "────────────────",
                "",
                f"{_pct(cur)}" if cur is not None else "—",
                "",
                "**Difference**",
                "",
                "────────────────",
                "",
                f"{_pct_delta(delta)}" if delta is not None else "—",
                "",
                f"{'✓' if c['passed'] else '❌'} {c['reason']}",
                "",
            ]
        )

    failed = [c for c in gate["checks"] if not c["passed"]]
    if failed:
        lines.append("### Merge blocked")
        lines.append("")
        for c in failed:
            lines.append(
                f"- **{c['name']}** — expected floor "
                f"`>{_pct(c['floor']) if c['floor'] is not None else 'n/a'}`; "
                f"actual `{_pct(c['current']) if c['current'] is not None else 'n/a'}`"
            )
        lines.append("")

    ref = gate.get("current_ref") or {}
    lines.extend(
        [
            "---",
            f"Queries evaluated: **{ref.get('queries_evaluated', '—')}** · "
            f"`{ref.get('strategy')}` / `{ref.get('mode')}` / `{ref.get('generator')}`",
            "",
            "_Gate: `contextiq-eval gate` · thresholds in `eval/ci/thresholds.json`_",
            "",
        ]
    )
    return "\n".join(lines)


def _pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def _pct_delta(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v * 100:.1f}%"


def run_gate(
    *,
    current_path: Path | None = None,
    baseline_path: Path | None = None,
    thresholds_path: Path | None = None,
    pr_label: str = "PR",
    baseline_label: str = "main",
) -> tuple[dict[str, Any], str]:
    current_path = current_path or DEFAULT_CURRENT
    baseline_path = baseline_path or DEFAULT_BASELINE
    thresholds_path = thresholds_path or DEFAULT_THRESHOLDS

    if not current_path.exists():
        raise FileNotFoundError(
            f"Missing current metrics at {current_path}. "
            "Run `contextiq-eval run` and commit docs/eval-results/rag-metrics.json"
        )
    if not baseline_path.exists():
        raise FileNotFoundError(f"Missing baseline at {baseline_path}")
    if not thresholds_path.exists():
        raise FileNotFoundError(f"Missing thresholds at {thresholds_path}")

    gate = evaluate_gate(
        current=_load_json(current_path),
        baseline=_load_json(baseline_path),
        thresholds=_load_json(thresholds_path),
    )
    md = render_markdown_report(
        gate, pr_label=pr_label, baseline_label=baseline_label
    )
    return gate, md


def promote_baseline(
    *,
    current_path: Path | None = None,
    baseline_path: Path | None = None,
) -> Path:
    current_path = current_path or DEFAULT_CURRENT
    baseline_path = baseline_path or DEFAULT_BASELINE
    current = _load_json(current_path)
    try:
        rel = str(current_path.relative_to(repo_root()))
    except ValueError:
        rel = str(current_path)
    payload = {
        "ref": "main",
        "updated_from": rel,
        "notes": "Promoted by contextiq-eval promote-baseline",
        "metrics": current.get("metrics"),
        "metrics_pct": current.get("metrics_pct"),
        "queries_evaluated": current.get("queries_evaluated"),
        "strategy": current.get("strategy"),
        "mode": current.get("mode"),
        "generator": current.get("generator"),
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return baseline_path
