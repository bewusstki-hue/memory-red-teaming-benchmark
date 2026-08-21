#!/usr/bin/env python3
"""
MRTB Prototype CLI

Beispiele:
    python cli.py run --adapter secure_reference
    python cli.py run --adapter vulnerable_reference
    python cli.py run --adapter secure_reference --scenario-dir scenarios --out reports
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from core.scenario import Scenario
from core.runner import run_scenario
from core.report import build_report, write_json, write_markdown

from adapters.reference_secure_adapter import SecureReferenceAdapter
from adapters.reference_vulnerable_adapter import VulnerableReferenceAdapter

ADAPTERS = {
    "secure_reference": SecureReferenceAdapter,
    "vulnerable_reference": VulnerableReferenceAdapter,
}


def main():
    parser = argparse.ArgumentParser(description="Memory Red-Teaming Benchmark - Prototyp")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Fuehrt alle Szenarien gegen einen Adapter aus")
    run_p.add_argument("--adapter", required=True, choices=sorted(ADAPTERS.keys()))
    run_p.add_argument("--scenario-dir", default="scenarios")
    run_p.add_argument("--out", default="reports")

    args = parser.parse_args()

    if args.command == "run":
        adapter_cls = ADAPTERS[args.adapter]
        adapter = adapter_cls()

        scenarios = Scenario.load_dir(args.scenario_dir)
        if not scenarios:
            print(f"Keine Szenarien in {args.scenario_dir} gefunden.", file=sys.stderr)
            sys.exit(1)

        out_dir = Path(args.out) / args.adapter
        trace_dir = out_dir / "traces"

        results = []
        print(f"\n=== MRTB Prototype Run: {adapter.name} ===\n")
        for sc in scenarios:
            res = run_scenario(adapter, sc, trace_dir)
            results.append(res)
            asr = f"{res.attack_success_rate*100:.0f}%" if res.repetitions else "-"
            print(f"[{res.verdict:11s}] {sc.id:55s} ASR={asr}")
            if res.verdict == "FAIL":
                first_fail = next((d.reason for d in res.details if not d.ok), None)
                print(f"              -> {first_fail}")
            if res.verdict == "UNSUPPORTED":
                print(f"              -> fehlende Capability: {res.unsupported_capability}")
            if res.verdict == "ERROR":
                print(f"              -> {res.error}")

        report = build_report(adapter.name, results)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(report, out_dir / "report.json")
        write_markdown(report, out_dir / "report.md")
        print(f"\nReport geschrieben nach: {out_dir}/report.md und report.json")
        print(f"Event-Traces geschrieben nach: {trace_dir}/\n")


if __name__ == "__main__":
    main()
