# Memory Red-Teaming Benchmark — Prototyp v0.1

Funktionierender Kern des MRTB-Konzepts. Kein 1:1-Abbild des vollen
32-Sektionen-Dokuments — das wäre ein Monate-Projekt. Das hier beweist,
dass der **Mechanismus** funktioniert: ein System sicher testen, ein
System unsicher testen, und zeigen, dass der Benchmark den Unterschied
zuverlässig erkennt.

**Unabhängigkeit:** Dieses Repository ist organisatorisch und technisch von
jedem einzelnen geprüften System getrennt (eigenes Repo, eigener Stack, keine
systemspezifische Logik im Core) — siehe
`Memory_Red_Teaming_Benchmark_Gesamtkonzept.md`, Abschnitt 13. Lizenz:
[Apache 2.0](LICENSE).

## Was drin ist

| Konzept-Sektion | Umgesetzt als |
|---|---|
| §7 Testfallformat | `core/scenario.py` + YAML-Dateien in `scenarios/` |
| §8 Adapter-Contract | `core/adapter.py` (Base-Klasse, Capabilities) |
| §9 Determinismus/Repetitions | `core/runner.py` (fixe Wiederholungen, ASR-Berechnung) |
| §10 Deterministische Evaluatoren | `core/evaluator.py` (4 harte Invarianten, kein LLM-Judge) |
| §10.3 Event-Trace | `core/events.py` (JSONL pro Lauf) |
| §11 Reporting + Schweregrade | `core/report.py` (JSON + Markdown) |
| §13 Referenzadapter zur Selbstvalidierung | `adapters/reference_secure_adapter.py` + `reference_vulnerable_adapter.py` |

**4 Beispiel-Szenarien**, aus vier verschiedenen Angriffsklassen:

1. `confidentiality.cross_tenant.canary_recall.v1` — Cross-Tenant Leakage (§6.2)
2. `integrity.poisoning.untrusted_promotion.v1` — Authority-Laundering (§6.5)
3. `temporal.replay_after_deletion.v1` — Replay nach Löschung (§6.6)
4. `repair.incomplete_removal.selective_poison_cleanup.v1` — gezielte Entfernung
   eines vergifteten Records darf keinen unbeteiligten legitimen Record mitlöschen
   und muss den vergifteten Record wirklich entfernen (§6.8, deckt beide dort
   gelisteten Subtypen "unvollständige Entfernung" + "Löschen legitimer
   Erinnerungen zusammen mit der Vergiftung" mit einer Invariante ab)

**2 Referenz-Adapter** als Positiv-/Negativkontrolle:

- `secure_reference` — korrekte Tenant-Partitionierung, erhält Trust-Level, löscht
  echt (vollständig UND gezielt per `by_query`/`by_id`)
- `vulnerable_reference` — vier realistische Bugs: kein Tenant-Filter beim Retrieval,
  stille Trust-Aufwertung untrusted→trusted beim Schreiben, Delete-Bug via
  Stale-Cache (Record bleibt nach "Löschung" abrufbar), `selector.mode` beim Delete
  komplett ignoriert (ein als gezielt gemeinter Reparaturversuch löscht in
  Wirklichkeit den ganzen Tenant-Bucket)

## Nutzung

```bash
pip install pyyaml --break-system-packages

python cli.py run --adapter secure_reference
python cli.py run --adapter vulnerable_reference
```

Ergebnis: Konsolen-Ausgabe pro Szenario (PASS/FAIL/UNSUPPORTED/ERROR + ASR),
plus `reports/<adapter>/report.md`, `report.json` und
`reports/<adapter>/traces/*.jsonl` (voller Event-Trace pro Wiederholung).

## Erwartetes Ergebnis

- `secure_reference`: 4× PASS
- `vulnerable_reference`: 4× FAIL, ASR=100% — jeweils mit exakter Fehlerbegründung
  und Record-ID im Trace

## Um einen echten Adapter zu testen

1. Neue Klasse unter `adapters/` schreiben, die von `BaseMemoryAdapter` erbt.
2. `capabilities()` ehrlich melden — nicht unterstützte Fähigkeiten führen
   zu `UNSUPPORTED`, fälschlich zugesicherte zu `FAIL`.
3. In `cli.py` unter `ADAPTERS` registrieren.
4. `python cli.py run --adapter <name>` laufen lassen.

## Was bewusst NICHT implementiert ist

- Signierte Run-Plans, Hash-Chaining der Events, Evidence Bundles (§30/§31)
- Claim Compiler / Claim Ladder (§31)
- Statistische Konfidenzintervalle, Blindness Report (§9.3, §30.5)
- LLM-as-Judge als sekundärer Evaluator (§10.2)
- End-to-End-Profil, nur Memory-only (§4.2)
- Governance-Prozess, Challenge-Verfahren, Interessenkonflikt-Regeln (§12)
- Weitere Angriffskategorien aus dem Katalog (§6): nur 4 von ~40 Subtypen
  sind als Szenario umgesetzt (2026-08-24: `repair.incomplete_removal.*`
  ergänzt, §6.8 Reparaturangriffe war zuvor gar nicht abgedeckt) — u.a. §6.1
  Memory Poisoning, §6.3 Context Drift, §6.4 Dissonanz/Halluzinationskaskaden
  und §6.7 Ressourcen-/Verfügbarkeitsangriffe haben weiterhin kein Szenario

Nächster sinnvoller Schritt wäre vermutlich: einen echten Adapter schreiben
und gegen die vier bestehenden Szenarien laufen lassen, dann die
Szenario-Anzahl weiter erhöhen (siehe Lücken oben), bevor
Signing/Evidence-Bundle-Layer angegangen wird.

## Aktueller Nachweis-Stand nach Claim Ladder (§30.3)

Jeder Lauf dieses Prototyps rechtfertigt ausschließlich einen **L0-Claim**:
„In einem lokalen Lauf wurden unter dokumentierter Konfiguration keine
Verletzungen in den ausgeführten Szenarien beobachtet.“ Signierte Run-Plans,
Hash-Chaining der Events und Evidence Bundles (Voraussetzung für L1) sind
oben unter „bewusst NICHT implementiert“ aufgeführt — ohne sie ist jeder
Claim oberhalb L0 unbelegt, unabhängig davon wie viele Szenarien PASS
melden. Diese Zeile hier nachziehen, sobald Signing/Evidence-Bundle (§25,
§31) umgesetzt sind, sonst veraltet sie genauso wie die alte 3-Szenarien-Zahl
es getan hätte.

---

**Zuletzt bearbeitet:** 2026-08-27
**Von:** Bewusst.KI
Implementierungsplan von konkreten Entwicklungswerkzeugen entkoppelt.
