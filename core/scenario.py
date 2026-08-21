"""
MRTB Core - Testfallformat (Section 7)
Bewusst reduziert gegenueber der vollen Spec: kein Abbruchregel-DSL,
kein Trace-Invariant-Matching - aber alle Pflichtfelder aus 7.1
(ID, Version, Kategorie, Profil, Capabilities, Angreifermodell,
Invarianten, Wiederholungszahl) sind vorhanden.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ScenarioStep:
    action: str  # write | retrieve | delete
    tenant: str
    session: str
    content: str | None = None
    query: str | None = None
    trust_level: str = "trusted"
    source_channel: str = "direct_user_input"
    selector_mode: str = "all"


@dataclass
class Scenario:
    id: str
    spec_version: str
    category: str
    profile: str
    requires: list[str]
    attacker: dict
    repetitions: int
    invariant: str
    setup: list[ScenarioStep]
    attack: list[ScenarioStep]
    raw: dict = field(default_factory=dict)

    @staticmethod
    def _steps(items: list[dict]) -> list[ScenarioStep]:
        return [
            ScenarioStep(
                action=i["action"],
                tenant=i["tenant"],
                session=i.get("session", "s1"),
                content=i.get("content"),
                query=i.get("query"),
                trust_level=i.get("trust_level", "trusted"),
                source_channel=i.get("source_channel", "direct_user_input"),
                selector_mode=i.get("selector", "all"),
            )
            for i in items
        ]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Scenario":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls(
            id=raw["id"],
            spec_version=raw.get("spec_version", "0.1.0"),
            category=raw["category"],
            profile=raw.get("profile", "memory_only"),
            requires=raw.get("requires", []),
            attacker=raw.get("attacker", {}),
            repetitions=int(raw.get("repetitions", 5)),
            invariant=raw["invariant"],
            setup=cls._steps(raw.get("setup", [])),
            attack=cls._steps(raw.get("attack", [])),
            raw=raw,
        )

    @classmethod
    def load_dir(cls, dir_path: str | Path) -> list["Scenario"]:
        p = Path(dir_path)
        return [cls.from_yaml(f) for f in sorted(p.glob("*.yaml"))]
