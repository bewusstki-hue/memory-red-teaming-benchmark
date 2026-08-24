"""
MRTB Core - Runner
Fuehrt ein Scenario mehrfach (repetitions) gegen einen Adapter aus,
erzeugt pro Lauf einen Event-Trace und aggregiert zu einem ScenarioResult
mit Attack Success Rate (Section 9.3, 11.1).
"""

from __future__ import annotations
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from core.adapter import (
    BaseMemoryAdapter, WriteContext, ReadContext, DeleteContext,
    MemoryInput, RecordSelector,
)
from core.scenario import Scenario, ScenarioStep
from core.evaluator import INVARIANT_REGISTRY, VerdictDetail
from core.events import EventTrace


@dataclass
class RepetitionResult:
    index: int
    ok: bool
    reason: str
    secret_token: str


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    verdict: str  # PASS | FAIL | UNSUPPORTED | ERROR
    repetitions: int
    attack_success_rate: float
    details: list[RepetitionResult] = field(default_factory=list)
    unsupported_capability: str | None = None
    error: str | None = None


def _missing_capability(adapter: BaseMemoryAdapter, requires: list[str]) -> str | None:
    caps = adapter.capabilities()
    for r in requires:
        if not getattr(caps, r, False):
            return r
    return None


def _substitute(text: str | None, secret: str) -> str | None:
    if text is None:
        return None
    return text.replace("${SECRET}", secret)


def _run_setup(adapter, trace: EventTrace, steps: list[ScenarioStep], secret: str):
    original_trust_level = "trusted"
    written_record_id = None
    for step in steps:
        adapter.create_tenant(step.tenant)
        adapter.create_session(step.tenant, step.session)
        if step.action == "write":
            content = _substitute(step.content, secret)
            ctx = WriteContext(
                tenant_id=step.tenant, session_id=step.session,
                source_channel=step.source_channel, trust_level=step.trust_level,
            )
            trace.emit("memory.write.requested", tenant=step.tenant,
                        trust_level=step.trust_level, source=step.source_channel)
            res = adapter.write(ctx, MemoryInput(content=content))
            trace.emit("memory.write.completed", tenant=step.tenant,
                        record_id=res.record_id, accepted=res.accepted)
            written_record_id = res.record_id
            original_trust_level = step.trust_level
        elif step.action == "delete":
            ctx = DeleteContext(tenant_id=step.tenant, session_id=step.session)
            selector_value = _substitute(step.query, secret)
            trace.emit("memory.delete.requested", tenant=step.tenant,
                        selector_mode=step.selector_mode, selector_value=selector_value)
            res = adapter.delete(ctx, RecordSelector(mode=step.selector_mode, value=selector_value))
            trace.emit("memory.delete.completed", tenant=step.tenant,
                        deleted_count=res.deleted_count)
    return original_trust_level, written_record_id


def run_scenario(adapter: BaseMemoryAdapter, scenario: Scenario,
                  trace_dir: str | Path) -> ScenarioResult:
    missing = _missing_capability(adapter, scenario.requires)
    if missing:
        return ScenarioResult(
            scenario_id=scenario.id, category=scenario.category,
            verdict="UNSUPPORTED", repetitions=0, attack_success_rate=0.0,
            unsupported_capability=missing,
        )

    invariant_fn = INVARIANT_REGISTRY.get(scenario.invariant)
    if invariant_fn is None:
        return ScenarioResult(
            scenario_id=scenario.id, category=scenario.category,
            verdict="ERROR", repetitions=0, attack_success_rate=0.0,
            error=f"Unbekannte Invariante: {scenario.invariant}",
        )

    trace_dir = Path(trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)

    details: list[RepetitionResult] = []
    try:
        for i in range(scenario.repetitions):
            adapter.reset()
            secret = f"CANARY-{secrets.token_hex(6)}"
            trace = EventTrace(scenario_id=f"{scenario.id}#{i}")

            original_trust_level, _ = _run_setup(adapter, trace, scenario.setup, secret)

            last_result = None
            attacker_ctx = None
            for step in scenario.attack:
                adapter.create_tenant(step.tenant)
                adapter.create_session(step.tenant, step.session)
                if step.action == "retrieve":
                    attacker_ctx = ReadContext(tenant_id=step.tenant, session_id=step.session)
                    query = _substitute(step.query, secret) or ""
                    trace.emit("memory.retrieve.requested", tenant=step.tenant, query=query)
                    last_result = adapter.retrieve(attacker_ctx, query)
                    trace.emit(
                        "memory.retrieve.returned", tenant=step.tenant,
                        record_ids=[r.id for r in last_result.records],
                    )
                elif step.action == "delete":
                    # Ergaenzung fuer Reparaturangriff-Szenarien (Section 6.8): bisher
                    # kannte nur die Setup-Phase "delete" (siehe _run_setup), ein
                    # gezielter Reparaturversuch als Teil des Angriffsablaufs selbst
                    # (nicht als Vorbedingung) fehlte.
                    delete_ctx = DeleteContext(tenant_id=step.tenant, session_id=step.session)
                    selector_value = _substitute(step.query, secret)
                    trace.emit("memory.delete.requested", tenant=step.tenant,
                                selector_mode=step.selector_mode, selector_value=selector_value)
                    delete_res = adapter.delete(delete_ctx, RecordSelector(mode=step.selector_mode, value=selector_value))
                    trace.emit("memory.delete.completed", tenant=step.tenant,
                                deleted_count=delete_res.deleted_count)

            if scenario.invariant == "tenant_isolation_no_leak":
                verdict: VerdictDetail = invariant_fn(attacker_ctx, last_result, secret)
            elif scenario.invariant == "no_untrusted_promoted_to_policy":
                verdict = invariant_fn(last_result, original_trust_level)
            elif scenario.invariant == "no_replay_after_deletion":
                verdict = invariant_fn(last_result, secret)
            elif scenario.invariant == "selective_repair_no_collateral_loss":
                # Konvention dieses Szenarios: die beiden geschriebenen Records
                # tragen den gemeinsamen Lauf-Secret als Praefix, unterschieden
                # durch ein festes Suffix (siehe scenarios/repair_selective_poison_removal.yaml).
                verdict = invariant_fn(last_result, f"{secret}-POISON", f"{secret}-LEGIT")
            else:
                verdict = VerdictDetail(False, "Kein Handler fuer Invariante implementiert.")

            trace.emit("invariant.checked", id=scenario.invariant,
                        status="pass" if verdict.ok else "fail", reason=verdict.reason)
            trace.write(trace_dir / f"{scenario.id.replace('.', '_')}__rep{i}.jsonl")

            details.append(RepetitionResult(index=i, ok=verdict.ok,
                                             reason=verdict.reason, secret_token=secret))
    except Exception as exc:  # noqa: BLE001
        return ScenarioResult(
            scenario_id=scenario.id, category=scenario.category,
            verdict="ERROR", repetitions=len(details), attack_success_rate=0.0,
            details=details, error=str(exc),
        )

    fails = sum(1 for d in details if not d.ok)
    asr = fails / len(details) if details else 0.0
    overall_verdict = "FAIL" if fails > 0 else "PASS"

    return ScenarioResult(
        scenario_id=scenario.id, category=scenario.category,
        verdict=overall_verdict, repetitions=len(details),
        attack_success_rate=asr, details=details,
    )
