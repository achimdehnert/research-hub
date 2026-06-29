# AGENT_HANDOVER · research-hub

> Führende Quelle für „was steht als nächstes an?". Beim Session-Ende aktualisieren
> (`/session-ende`). Der Session-Start-Hook liest die Sektion `## Prioritäten`.
> AI-Research-Plattform (Django + Celery + pgvector). Prod: https://research.iil.pet
> Server `88.198.191.108`, Compose-Service `research-hub-web`, Port 8098.

## Stand 2026-06-29 (Session 4) — Onboarding-SSoT + research-App-Architektur-Refactors (5 PRs, alle live)

**Aktueller Zustand:** `main` = `origin/main` (`5a112ee`), Working-Tree clean, keine offenen Worktrees.
**Prod aktuell & grün:** Deploy-Run 28407848157 (sha `5a112ee`) success; `https://research.iil.pet/healthz/` → HTTP 200. Migration `0010` (SoftDelete, rein State) live.

**Diese Session — 5 PRs gemergt:**
- **#33** docs: `CLAUDE.md` als alleinige SSoT (Port 8098, Health-Semantik `/livez`=liveness, `/healthz`=readiness, Apps-Map, Run/Test, Branch-Guard); stale `docs/AGENT_HANDOVER.md` (gelöster 502-Incident als „offen") gelöscht; `catalog-info.yaml` Incident-Doppel-Imagename korrigiert.
- **platform #721** fix(registry): research-hub-Port 8104→8098 in 4 Registries (Generator-Quelle `scripts/repo-registry.yaml` u.a.). Ground Truth: `nginx.conf` proxy_pass 8098 + `docker-compose.prod.yml:70`. Danach `gen-project-facts` → `project-facts.md` = 8098.
- **#34** chore: toten `env_loader.py`-Symlink entfernt; zwei `Dockerfile` mit Rollen-Banner (root `./Dockerfile`=kanonisch Prod/CI via shared-ci, `docker/Dockerfile`=nur Dev-Stack).
- **#35** refactor(A1+A2): `SoftDeleteManager` als Default-Manager (`objects`=alive-only, `all_objects`+`alive()/dead()`, `Meta.base_manager_name='all_objects'`); Lösch-Kaskade zentral in `apps/research/soft_delete.py` (3× Duplikat in Delete-Views weg).
- **#36** refactor(A4): Prompt-Fallback aus kanonischer `prompts/research-hub-seed.yaml` via `config/prompt_fallback.py` statt hand-divergenter Inline-f-Strings; beide Call-Sites (`research/services._deep_analyze` + `knowledge/tasks`).

**Verifikation:** volle Test-Suite **115 passed** (lokal gegen Test-Postgres); jede PR-CI grün; Prod-Health 200.
**Hinweis:** orchestrator-pgvector-Memory war headless nicht erreichbar (HTTP 404) → Session-Summary nur datei-basiert (`~/.claude/.../memory/promptfw-seed-not-applied.md`) + hier.

## Stand 2026-06-24 (Session 3) — Retro + Cross-Repo-Aufräumen abgeschlossen

**Aktueller Zustand:** `main` = `origin/main` (`f63b325`), Working-Tree clean.
Letzter Deploy grün (Run 28093087390, sha 6448548). Remote nur noch `main`.
**Ein offenes Issue: #26** (Infra-Drift) — bewusst für platform-Session geparkt (s. Prioritäten).

**Session 3 (2026-06-24) — Retro + Cross-Repo-Aufräumen:**
- **Session-Retro** abgeschlossen: `~/shared/session-retro-2026-06-24-research-hub-46c50c.md` (4 Survivors, 4 REFUTED).
- **3 Zombie-Issues geschlossen:** `recruiting-hub #1`, `researchfw #1`, `weltenfw #2` (Fix war bereits gemergt, kein `Closes #n` in PRs).
- **weltenhub #11:** STOP-Kommentar hinterlassen (pre-existing CI-Failures, PR #12).
- **writing-hub gescannt:** 4 Issues, alle STOP (Cross-Repo/Migration/ADR/Epic) — kein DO-NOW.
- **promptfw PR #14 + Issue #11 geschlossen:** main war seit 2026-06-22 grün (PRs #15/#16 hatten Lint bereits gefixt), PR hatte unlösbare Merge-Konflikte.

**Session 2 (2026-06-24) — /issues-offen org:achimdehnert (6 Läufe, 48/49 Repos):**
- Org-weiter Issue-Scan (achimdehnert, 49 Repos): **0 DO-NOW** auf main.
- **weltenhub PR #12** (noqa-fix): Lint ✅, Tests rot pre-existing (platform-context + django_tenancy).

**Session 1 — diese Session erledigt:**
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

> Neuer **Architektur-Backlog** aus der `research`-App-Analyse (2026-06-29). Optionale, gate-freie Folge-PRs — kein Pflicht-Strang.

1. **research-App Architektur-Findings** (Analyse 2026-06-29, je 1 PR):
   - **A3** Status-State-Machine — Übergänge `draft→running→analysing→done/error` kapseln (heute verstreut über `tasks.py` + `services.py`, Race-Risiko bei Retry).
   - **A5** totes `academic_sources`-Feld + `ACADEMIC_SOURCE_CHOICES` deprecaten (iil_researchfw ignoriert es; im `forms.py`-NOTE dokumentiert).
   - **A6** Middleware-Order-Assert — Tenant-Isolation hängt implizit an `AuthenticationMiddleware` VOR `ResearchHubTenantMiddleware` (heute korrekt, `base.py:80<85`; Reorder bricht Isolation still).
   - **A7** `views_metrics.py` (397 LOC) in `metrics/`-Subpackage splitten (Auth/Collectors/Exporter).
   - **NEU** promptfw-DB-Seeding im `entrypoint` (`seed_prompts` aus der YAML) — aktuell wird nichts geseedet, der YAML-Fallback ist der aktive Prod-Pfad (Memory `promptfw-seed-not-applied`).
2. **#26 (Infra-Drift) NICHT in research-hub fixen** — platform-Scope (shared-ci-tag-stale), `/ci-green-program`. Nur beobachten.
3. Optional: `/teste-repo` (lokal via `docker-compose.test.yml`).

> **Erledigt Session 4 (2026-06-29):** Onboarding-SSoT-Konsolidierung (#33/#721/#34) + research-App-Refactors A1/A2/A4 (#35/#36). research-App-Architektur analysiert; A3/A5/A6/A7 + promptfw-Seeding als Backlog oben.
> **Erledigt Session 3 (2026-06-24):** Zombie-Issues geschlossen (recruiting-hub/researchfw/weltenfw), weltenhub #11 kommentiert (PR #12 geparkt bis platform-ci-Paket), writing-hub gescannt (alle STOP), promptfw PR #14 + Issue #11 geschlossen.

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
