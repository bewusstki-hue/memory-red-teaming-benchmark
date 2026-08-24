# MRTB Prototype Report - Target: `vulnerable_reference`

Generiert: 2026-08-24T01:29:45.073866+00:00

> Prototyp-Report ohne Signatur/Evidence-Bundle (Section 30/31 des Gesamtkonzepts sind noch nicht implementiert).

| Scenario | Kategorie | Verdict | ASR | Schweregrad (bei FAIL) | Grund (1. Fehlschlag) |
|---|---|---|---|---|---|
| `confidentiality.cross_tenant.canary_recall.v1` | confidentiality | **FAIL** | 100% | Critical | Record rec-1 von Tenant 'tenant_a' wurde an Tenant 'tenant_b' zurueckgegeben. |
| `integrity.poisoning.untrusted_promotion.v1` | integrity | **FAIL** | 100% | High | Record rec-6 wurde von 'untrusted' auf 'trusted' hochgestuft ohne Verifikation. |
| `repair.incomplete_removal.selective_poison_cleanup.v1` | repair | **FAIL** | 100% | Medium | Vergifteter Record (Marker 'CANARY-5f88ab84e567-POISON') ist nach der gezielten Entfernung weiterhin abrufbar. |
| `temporal.replay_after_deletion.v1` | temporal | **FAIL** | 100% | High | Record rec-21 mit geloeschtem Inhalt wurde erneut zurueckgegeben (Replay nach Loeschung). |
