"""
MRTB Core - Reporting (Section 11)
Trennt Saeulenscores klar, keine Kompensation eines kritischen
Confidentiality-Fails durch andere gute Ergebnisse.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from core.runner import ScenarioResult

SEVERITY_BY_CATEGORY = {
    "confidentiality": "Critical",
    "integrity": "High",
    "temporal": "High",
}


def build_report(adapter_name: str, results: list[ScenarioResult]) -> dict:
    return {
        "mrtb_prototype_version": "0.1.0-proto",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_adapter": adapter_name,
        "note": (
            "Prototyp-Report ohne Signatur/Evidence-Bundle (Section 30/31 "
            "des Gesamtkonzepts sind noch nicht implementiert)."
        ),
        "results": [
            {
                "id": r.scenario_id,
                "category": r.category,
                "severity_if_fail": SEVERITY_BY_CATEGORY.get(r.category, "Medium"),
                "verdict": r.verdict,
                "repetitions": r.repetitions,
                "attack_success_rate": r.attack_success_rate,
                "unsupported_capability": r.unsupported_capability,
                "error": r.error,
                "first_failure_reason": next(
                    (d.reason for d in r.details if not d.ok), None
                ),
            }
            for r in results
        ],
    }


def write_json(report: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(report: dict, path: str | Path) -> None:
    lines = [
        f"# MRTB Prototype Report - Target: `{report['target_adapter']}`",
        "",
        f"Generiert: {report['generated_at']}",
        "",
        f"> {report['note']}",
        "",
        "| Scenario | Kategorie | Verdict | ASR | Schweregrad (bei FAIL) | Grund (1. Fehlschlag) |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        asr = f"{r['attack_success_rate']*100:.0f}%" if r["repetitions"] else "-"
        verdict_marker = {
            "PASS": "PASS",
            "FAIL": "**FAIL**",
            "UNSUPPORTED": "UNSUPPORTED",
            "ERROR": "ERROR",
        }.get(r["verdict"], r["verdict"])
        reason = r["first_failure_reason"] or (r["unsupported_capability"] or r["error"] or "-")
        lines.append(
            f"| `{r['id']}` | {r['category']} | {verdict_marker} | {asr} | "
            f"{r['severity_if_fail'] if r['verdict']=='FAIL' else '-'} | {reason} |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
