"""
MRTB Core - Adapter Contract
Entspricht Sektion 8 des Gesamtkonzepts: einheitliches Protokoll,
das jedes Memory-/Agenten-System implementieren muss, um getestet
zu werden. Der Adapter selbst enthaelt keine Testlogik und keine
Bevorzugung - er uebersetzt nur zwischen Testprotokoll und System-API.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class MemoryCapabilities:
    """Capability Discovery (Section 8.3). Fehlende Capabilities fuehren
    im Runner zu UNSUPPORTED statt zu einem stillschweigenden PASS."""
    write: bool = False
    retrieve: bool = False
    delete: bool = False
    list_records: bool = False
    clear_session: bool = False
    clear_tenant: bool = False
    tenant_isolation: bool = False
    provenance: bool = False
    temporal_metadata: bool = False
    deterministic_mode: bool = False

    def supports(self, *names: str) -> bool:
        return all(getattr(self, n, False) for n in names)


@dataclass
class WriteContext:
    tenant_id: str
    session_id: str
    actor: str = "user"
    source_channel: str = "direct_user_input"  # z.B. retrieved_document, tool_return, agent_self_write
    trust_level: str = "trusted"  # trusted | untrusted | unknown


@dataclass
class ReadContext:
    tenant_id: str
    session_id: str
    actor: str = "user"


@dataclass
class DeleteContext:
    tenant_id: str
    session_id: str
    actor: str = "user"


@dataclass
class MemoryInput:
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryRecord:
    id: str
    tenant_id: str
    session_id: str
    content: str
    metadata: dict = field(default_factory=dict)
    trust_level: str = "trusted"
    source_channel: str = "direct_user_input"
    deleted: bool = False


@dataclass
class WriteResult:
    record_id: Optional[str]
    accepted: bool


@dataclass
class RetrievalResult:
    records: list[MemoryRecord] = field(default_factory=list)


@dataclass
class DeleteResult:
    deleted_count: int


@dataclass
class RecordSelector:
    mode: str = "all"  # all | by_id | by_query
    value: Optional[str] = None


class BaseMemoryAdapter:
    """Referenz-Interface, siehe Section 8.2. Jeder zu testende Adapter
    erbt hiervon. Kein zusaetzlicher Zustand darf zwischen reset()-Aufrufen
    ueberleben."""

    name: str = "unnamed-adapter"

    def capabilities(self) -> MemoryCapabilities:
        raise NotImplementedError

    def create_tenant(self, tenant_id: str) -> None:
        raise NotImplementedError

    def create_session(self, tenant_id: str, session_id: str) -> None:
        raise NotImplementedError

    def write(self, context: WriteContext, content: MemoryInput) -> WriteResult:
        raise NotImplementedError

    def retrieve(self, context: ReadContext, query: str) -> RetrievalResult:
        raise NotImplementedError

    def delete(self, context: DeleteContext, selector: RecordSelector) -> DeleteResult:
        raise NotImplementedError

    def clear_session(self, tenant_id: str, session_id: str) -> None:
        raise NotImplementedError

    def clear_tenant(self, tenant_id: str) -> None:
        raise NotImplementedError

    def list_records(self, context: ReadContext) -> list[MemoryRecord]:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError
