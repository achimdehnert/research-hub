---
title: "ADR-001: Klickdummy Research-Workflow"
status: Accepted
date: 2026-07-14
deciders: Achim Dehnert
scope: research-hub
conforms_to: platform:ADR-211
tags: [klickdummy]
class: spec-demo
sunset_after: "2027-07-14"
extension_review_required: false
related: []
---

# ADR-001: Klickdummy Research-Workflow

## Kontext

`/kd-scout research-hub`-Lauf (2026-07-14, Klickdummy-Rollout-Queue, Issue
[iilgmbh/iil-klickdummy#176](https://github.com/iilgmbh/iil-klickdummy/issues/176))
identifizierte `apps/research` als Anker-Kandidat: die
Workspace→Project→ResearchProject-Hierarchie ist der Produkt-Wertkern.

Erste Adoption von `iil-klickdummy` in diesem Repo (kein vorheriges KD-Setup,
kein vorheriges `docs/adr/`, **kein vorheriges Makefile** — research-hub
nutzte bisher pip/ruff/pytest direkt ohne Make-Abstraktion, analog dms-hub).
Diese ADR verankert Tooling und Klickdummy in einem Schritt.

## Entscheidung

Klasse **`spec-demo`** (nicht `mock`): alle zugrunde liegenden Routen
existieren real und laufen (`apps/research/views.py`).

**Prod-Guard (I2-Externprobe):**
- Query-Parameter `?demo=on` aktiviert den Demo-Render.
- Serverseitiger Flag `KLICKDUMMY_DEMO_ENABLED` (Default `False`) UND
  `settings.DEBUG=True` müssen beide gesetzt sein — `config/settings/production.py:7`
  setzt `DEBUG` bereits hart auf `False`.
- **Noch nicht implementiert** (dieser PR liefert nur Spec + ADR + Tooling,
  keinen Guard-Code in `apps/research` selbst). Vor Prod-Wirksamkeit dieses
  Musters ist der Guard nachzuziehen (Folge-Issue, s. Konsequenzen).

3 Screens, aus echtem Code extrahiert (brownfield):

- `workspace-uebersicht` — alle Workspaces mit berechneter Research-Anzahl (`WorkspaceListView`)
- `research-anlegen` — Recherche-Anfrage-Formular (`ResearchCreateView`)
- `research-status` — Status-Pipeline `draft → running → analysing → done|error` (`ResearchProject.status`)

## Konsequenzen

- **Tooling-Erstadoption inkl. neuem Makefile:** research-hub hatte zuvor
  kein Makefile. Dieser PR legt ein **minimales** Makefile an, das **nur**
  die Klickdummy-Targets enthält — keine Nachbildung der bestehenden
  CI-Pipeline.
- `docs/adr/` **neu angelegt** — Repo hatte zuvor kein ADR-Verzeichnis.
  Diese ADR ist damit `ADR-001`.
- CI-Gate (`klickdummy`-Job in `.github/workflows/ci.yml`) im selben PR
  verdrahtet, als eigenständiger Sibling-Job.
- **Folge-Issue nötig:** der `KLICKDUMMY_DEMO_ENABLED`+`?demo=on`-Guard ist in
  diesem PR nur in Spec/ADR deklariert, nicht in `apps/research`
  implementiert. Kein I2-Verstoß (Policy: `klickdummy_prod_guard.sh` ist laut
  `~/.claude/policies/klickdummy.md` Rev 20 selbst noch unimplementiert/dormant),
  aber im Repo offen zu tracken.
- Auto-Deploy-on-Merge: `deploy.yml` triggert auf jeden Push nach `main` (kein
  `paths-ignore`) — ein Merge dieses PRs löst einen echten Production-Deploy
  von research-hub aus (Memory `prod-deploy-preflight-before-merge-approval`).

## Bezug

- `platform:ADR-211` — Klickdummy-Konvention
- `apps/research/models.py` — `Workspace`, `Project`, `ResearchProject`
- `apps/research/views.py` — `WorkspaceListView`, `ResearchCreateView`, `ResearchStatusView`
- `config/settings/production.py:7` — `DEBUG = False` (Basis des Prod-Guards)
- Issue #176 (iil-klickdummy) — Klickdummy-Rollout-Queue
