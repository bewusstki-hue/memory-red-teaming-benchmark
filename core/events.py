"""
MRTB Core - Event Trace
JSONL-Ereigniskette pro Lauf. Bewusst simpel gehalten: kein Hash-Chaining,
kein Signing - das ist Teil der spaeteren Evidence-Bundle-Ausbaustufe
(Section 30/31), nicht des Prototyps.
"""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field


@dataclass
class EventTrace:
    scenario_id: str
    events: list[dict] = field(default_factory=list)

    def emit(self, event: str, **fields) -> None:
        self.events.append({
            "ts": round(time.time(), 6),
            "scenario": self.scenario_id,
            "event": event,
            **fields,
        })

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e, ensure_ascii=False) for e in self.events)

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_jsonl())
            f.write("\n")
