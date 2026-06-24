# AGENT_HANDOVER · research-hub

> Führende Quelle für „was steht als nächstes an?". Beim Session-Ende aktualisieren
> (`/session-ende`). Der Session-Start-Hook liest die Sektion `## Prioritäten`.
> AI-Research-Plattform (Django + Celery + pgvector). Prod: https://research.iil.pet
> Server `88.198.191.108`, Compose-Service `research-hub-web`, Port 8098.

## Stand 2026-06-24 — synced, grün, Test-Setup repariert + Warnungen weg

**Aktueller Zustand:** `main` = `origin/main` (`6448548`), Working-Tree clean.
Letzter Deploy grün (Run 28093087390, sha 6448548). Remote nur noch `main`.
**Ein offenes Issue: #26** (Infra-Drift) — bewusst für platform-Session geparkt (s. Prioritäten).

**Diese Session erledigt:**
- `/teste-repo` gefahren: 102 „Fehler" als reine Infrastruktur entlarvt (fehlendes
  Postgres + Port-5434-Kollision mit `writing_hub_db_dev`), kein Code-Defekt.
  Beweis: pytest gegen CI-konformes Postgres → **104 passed**.
- **PR #23** — Test-DB-Defaults repariert: Standalone-Defaults von Unix-Socket +
  User `dehnert` (nur Lead-Dev-Maschine) auf erreichbares TCP `127.0.0.1:5439`
  umgestellt + `docker/docker-compose.test.yml` (pgvector) ergänzt, das genau
  diese Defaults bedient. shared-CI-Pfad (`POSTGRES_HOST`) mustergleich zu
  writing-hub. `ci.yml` unverändert (pinnt `TEST_DB_*` explizit).
- **PR #24** — iil-testkit-Warnungen aufgeräumt: `iil_repo_type = "django"`
  (ADR-058) + Marker `f1/f3/a2/a6/u3` registriert und semantisch an je einen
  Test gehängt → „ADR-058 Compliance PASSED"; 12 Tests auf `test_should_*`
  umbenannt (ADR-057).
- Branch-Cleanup: 5 gemergte stale Remote-Branches gelöscht (PRs #11/#15/#20/#21/#22,
  je gegen PR-Merge-Status geprüft — nicht `git cherry`, wg. Squash-Divergenz).
- **Issue #26** (Infra-Drift, 4 pre-existing Errors aus `drift_check.py`): 2 von 4
  behoben — **PR #27** (`requirements.txt` Top-Level angelegt; `HEALTHCHECK` aus
  Dockerfile entfernt, ADR-078, Compose prüft `/healthz/` bereits) + **PR #28**
  (`_ci-python`-Pin v1.0.6 → v1.0.8, Tag-Alignment, Warn weg). Drift-Recheck: 4→2 Errors.
- Root-Cause der 2 verbleibenden `shared-ci-tag-stale`-Errors geklärt: **kein
  research-hub-Fix** — `platform/main` hinkt shared-ci `v1.0.8` hinterher
  (`migrations_smoke` / `ghcr_push_token` fehlen im platform-Mirror). Gehört in
  eine platform-Governance-Session; #26 dafür offen gelassen.

**Zuletzt gemergt (heute, 2026-06-24):**
- #23 fix(test): erreichbare DB-Defaults + `docker-compose.test.yml`
- #24 chore(test): ADR-057-Naming + ADR-058-Taxonomy-Warnungen auflösen
- #25 docs: AGENT_HANDOVER auf Stand 2026-06-24
- #27 fix(infra): requirements.txt + Dockerfile-HEALTHCHECK entfernt (#26)
- #28 chore(ci): _ci-python Pin v1.0.6 → v1.0.8 (#26)

## Prioritäten

> Keine angefangene research-hub-Arbeit zum Fortsetzen. Ein Issue ist offen,
> aber bewusst **platform-Scope** (nicht hier lösbar). Reihenfolge = Vorschlag.

1. **#26 (Infra-Drift) NICHT in research-hub fixen** — die 2 verbleibenden
   `shared-ci-tag-stale`-Errors sind ein platform↔shared-ci-Mirror-Thema
   (`platform/main` hinkt shared-ci `v1.0.8` hinterher). Gehört in eine
   platform-Governance-Session (`/ci-green-program`), nicht in einen
   research-hub-Edit. Hier nur beobachten.
2. Sonst kein offener Backlog — neues Thema/Issue definieren, dann passend routen.
3. Optional: `/teste-repo` (jetzt lokal reproduzierbar via `docker-compose.test.yml`).

## Wo gestartet?

```bash
cd ~/github/research-hub
git fetch origin && git status -sb        # main = origin/main? clean?

# Lokal hochfahren (Django + Celery + Postgres/pgvector via Compose, Port 8098)
docker compose -f docker/docker-compose.yml up -d
curl http://127.0.0.1:8098/healthz/        # Health-Probe

# Tests (kein Makefile — Test-Postgres via Compose, dann pytest mit Test-Settings)
docker compose -f docker/docker-compose.test.yml up -d   # pgvector auf 127.0.0.1:5439
DJANGO_SETTINGS_MODULE=config.settings.test pytest
docker compose -f docker/docker-compose.test.yml down     # aufräumen

gh pr list && gh issue list                # offene Arbeit prüfen
```

> Hinweis: Direkt-Commits auf `main` sind durch den `main-tree-guard` (platform:ADR-233)
> blockiert. Editierende Arbeit gehört in einen Feature-Branch / Worktree
> (`git worktree add /tmp/<slug> -b <branch> origin/main`) und läuft über PR.
