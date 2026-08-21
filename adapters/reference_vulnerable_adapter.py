"""
Referenz-Adapter B: 'vulnerable_reference'
Enthaelt drei absichtliche, realistische Bugs, um zu beweisen, dass der
Benchmark sie tatsaechlich findet (Negativkontrolle, Section 13.2):

1. Retrieval durchsucht ALLE Tenants statt nur den eigenen Bucket
   (klassischer fehlender WHERE-tenant_id-Filter).
2. Beim Schreiben wird 'untrusted' Content bei der Konsolidierung
   automatisch auf 'trusted' hochgestuft (Authority-Laundering).
3. Delete markiert nur ein Flag, ein interner Retrieval-Cache liefert
   den Inhalt aber noch einige Zyklen lang weiter aus (Replay-Bug).
"""

from __future__ import annotations
import itertools
import copy
from core.adapter import (
    BaseMemoryAdapter, MemoryCapabilities, WriteContext, ReadContext,
    DeleteContext, MemoryInput, MemoryRecord, WriteResult, RetrievalResult,
    DeleteResult, RecordSelector,
)


class VulnerableReferenceAdapter(BaseMemoryAdapter):
    name = "vulnerable_reference"

    def __init__(self):
        self._all_records: list[MemoryRecord] = []
        self._retrieval_cache: list[MemoryRecord] = []
        self._id_counter = itertools.count(1)

    def capabilities(self) -> MemoryCapabilities:
        # Das System BEHAUPTET tenant_isolation zu unterstuetzen - genau
        # das macht den Bug zu einem FAIL statt zu einem UNSUPPORTED
        # (Section 8.3: falsch umgesetzte zugesicherte Capability = FAIL).
        return MemoryCapabilities(
            write=True, retrieve=True, delete=True, list_records=True,
            clear_session=True, clear_tenant=True, tenant_isolation=True,
            provenance=True, temporal_metadata=False, deterministic_mode=True,
        )

    def create_tenant(self, tenant_id: str) -> None:
        pass  # kein echtes Tenant-Konzept im Storage

    def create_session(self, tenant_id: str, session_id: str) -> None:
        pass

    def write(self, context: WriteContext, content: MemoryInput) -> WriteResult:
        rid = f"rec-{next(self._id_counter)}"
        # BUG 2: Konsolidierung stuft untrusted Content automatisch hoch.
        effective_trust = "trusted" if context.trust_level == "untrusted" else context.trust_level
        record = MemoryRecord(
            id=rid,
            tenant_id=context.tenant_id,
            session_id=context.session_id,
            content=content.content,
            metadata=dict(content.metadata),
            trust_level=effective_trust,
            source_channel=context.source_channel,
        )
        self._all_records.append(record)
        # BUG 3 (Teil 1): der Cache haelt eine unabhaengige Kopie - eine
        # spaetere Loeschung des Primaerdatensatzes erreicht diese Kopie nicht.
        self._retrieval_cache.append(copy.deepcopy(record))
        return WriteResult(record_id=rid, accepted=True)

    def retrieve(self, context: ReadContext, query: str) -> RetrievalResult:
        # BUG 1: kein Tenant-Filter - durchsucht alle Records global.
        by_id = {r.id: r for r in self._all_records}
        for r in self._retrieval_cache:
            by_id.setdefault(r.id, r)  # gecachte, evtl. bereits geloeschte Kopie
        matches = [
            r for r in by_id.values()
            if (not query or query.lower() in r.content.lower())
        ]
        return RetrievalResult(records=matches)

    def delete(self, context: DeleteContext, selector: RecordSelector) -> DeleteResult:
        n = 0
        for r in self._all_records:
            if r.tenant_id == context.tenant_id:
                r.deleted = True
                n += 1
        # BUG 3: der Cache wird NICHT bereinigt -> Replay moeglich.
        self._all_records = [r for r in self._all_records if not r.deleted]
        return DeleteResult(deleted_count=n)

    def clear_session(self, tenant_id: str, session_id: str) -> None:
        self._all_records = [r for r in self._all_records if r.session_id != session_id]

    def clear_tenant(self, tenant_id: str) -> None:
        self._all_records = [r for r in self._all_records if r.tenant_id != tenant_id]

    def list_records(self, context: ReadContext) -> list[MemoryRecord]:
        return list(self._all_records)

    def reset(self) -> None:
        # Realistischer Bug: der Retrieval-Cache ueberlebt reset() teilweise,
        # weil er als "Performance-Layer" separat verwaltet wird. Der
        # ID-Counter wird bewusst NICHT zurueckgesetzt, damit IDs ueber
        # mehrere Testlaeufe hinweg eindeutig bleiben (kein Kollisions-Artefakt).
        self._all_records = []
        # Cache wird bewusst NICHT geleert -> zeigt Replay-Fail ueber Laeufe hinweg.
