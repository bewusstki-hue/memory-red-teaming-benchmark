"""
Referenz-Adapter A: 'secure_reference'
Absichtlich sauber implementiert - dient als Positivkontrolle, um zu
zeigen, dass die Testmaschine ein korrektes System auch als korrekt
erkennt (Section 13.2, Punkt 2: 'Referenzadapter und bewusst unsicherer
Adapter beweisen, dass Tests Passes und Failures erkennen.')
"""

from __future__ import annotations
import itertools
from core.adapter import (
    BaseMemoryAdapter, MemoryCapabilities, WriteContext, ReadContext,
    DeleteContext, MemoryInput, MemoryRecord, WriteResult, RetrievalResult,
    DeleteResult, RecordSelector,
)


class SecureReferenceAdapter(BaseMemoryAdapter):
    name = "secure_reference"

    def __init__(self):
        self._store: dict[str, list[MemoryRecord]] = {}
        self._id_counter = itertools.count(1)

    def capabilities(self) -> MemoryCapabilities:
        return MemoryCapabilities(
            write=True, retrieve=True, delete=True, list_records=True,
            clear_session=True, clear_tenant=True, tenant_isolation=True,
            provenance=True, temporal_metadata=True, deterministic_mode=True,
            selective_delete=True,
        )

    def create_tenant(self, tenant_id: str) -> None:
        self._store.setdefault(tenant_id, [])

    def create_session(self, tenant_id: str, session_id: str) -> None:
        self.create_tenant(tenant_id)

    def write(self, context: WriteContext, content: MemoryInput) -> WriteResult:
        self.create_tenant(context.tenant_id)
        rid = f"rec-{next(self._id_counter)}"
        record = MemoryRecord(
            id=rid,
            tenant_id=context.tenant_id,
            session_id=context.session_id,
            content=content.content,
            metadata=dict(content.metadata),
            # Provenienz wird 1:1 erhalten - keine stille Trust-Aufwertung.
            trust_level=context.trust_level,
            source_channel=context.source_channel,
        )
        self._store[context.tenant_id].append(record)
        return WriteResult(record_id=rid, accepted=True)

    def retrieve(self, context: ReadContext, query: str) -> RetrievalResult:
        # Harte Tenant-Partitionierung: nur der eigene Tenant-Bucket wird durchsucht.
        bucket = self._store.get(context.tenant_id, [])
        matches = [
            r for r in bucket
            if not r.deleted and (not query or query.lower() in r.content.lower())
        ]
        return RetrievalResult(records=matches)

    def delete(self, context: DeleteContext, selector: RecordSelector) -> DeleteResult:
        bucket = self._store.get(context.tenant_id, [])
        if selector.mode == "all":
            n = len([r for r in bucket if not r.deleted])
            # Echte Loeschung, kein Soft-Delete, kein Replay-faehiger Cache.
            self._store[context.tenant_id] = []
            return DeleteResult(deleted_count=n)
        if selector.mode == "by_query" and selector.value:
            # Gezielte Entfernung (Section 6.8-Gegenstueck): nur passende Records
            # verlassen den Bucket, unbeteiligte Records bleiben unangetastet --
            # echte Loeschung wie beim "all"-Fall, kein Soft-Delete.
            needle = selector.value.lower()
            kept = [r for r in bucket if needle not in r.content.lower()]
            n = len(bucket) - len(kept)
            self._store[context.tenant_id] = kept
            return DeleteResult(deleted_count=n)
        if selector.mode == "by_id" and selector.value:
            kept = [r for r in bucket if r.id != selector.value]
            n = len(bucket) - len(kept)
            self._store[context.tenant_id] = kept
            return DeleteResult(deleted_count=n)
        return DeleteResult(deleted_count=0)

    def clear_session(self, tenant_id: str, session_id: str) -> None:
        self._store[tenant_id] = [
            r for r in self._store.get(tenant_id, []) if r.session_id != session_id
        ]

    def clear_tenant(self, tenant_id: str) -> None:
        self._store[tenant_id] = []

    def list_records(self, context: ReadContext) -> list[MemoryRecord]:
        return list(self._store.get(context.tenant_id, []))

    def reset(self) -> None:
        self._store = {}
        self._id_counter = itertools.count(1)
