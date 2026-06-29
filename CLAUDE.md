# CLAUDE.md · research-hub

> **Single Source of Truth für Agenten.** Diese Datei zuerst lesen. Bei Konflikt
> mit anderen Docs gilt: **Code > diese Datei > alles andere.** Stand-/Backlog-Fragen
> („was als nächstes?") beantwortet `AGENT_HANDOVER.md` (führend, per `/session-ende` gepflegt).

AI-Research-Plattform (World-Building, Epochen, Orte, Namen). Django 5 + HTMX,
PostgreSQL 16 + pgvector, Celery + Redis. Aufbauend auf dem PyPI-Paket `iil-researchfw`.

## Kanonische Fakten (Code-verifiziert)

| Fakt | Wert | Beleg |
|---|---|---|
| Prod-URL | `https://research.iil.pet` | – |
| Staging-URL | `https://staging.research.iil.pet` | – |
| Server (Hetzner) | `88.198.191.108`, Pfad `/opt/research-hub` | catalog-info.yaml |
| **Port** | **8098** (`127.0.0.1:8098 → :8000`) | `docker-compose.prod.yml:70` |
| Prod-Image | `ghcr.io/${GHCR_OWNER:-achimdehnert}/${GHCR_REPO:-research-hub}:${IMAGE_TAG}` | `docker-compose.prod.yml:57,95` |
| Compose-Service | `research-hub-web` | – |
| DB-Name / -Container | `research_hub` / `research_hub_db` | – |
| Lokaler Pfad (dieser Host) | `~/github/research-hub` | – |

### Health-Endpoints (beide existieren, `config/urls.py:22-23`)
- `GET /livez/` → **Liveness** · `{"status":"alive"}` — Prozess lebt.
- `GET /healthz/` → **Readiness** · `{"status":"ok","service":"research-hub"}` — Prod-Compose-Healthcheck probt diesen.

## Apps (`apps/`, größte zuerst)

| App | LOC | Rolle |
|---|---|---|
| `research` | ~2.6k | Kern-Domäne: World-Building-Entitäten, Services, API (`/api/v1/`), Metrics |
| `knowledge` | ~0.9k | Knowledge-Dashboard / -Hierarchie (`/knowledge/`) |
| `documents` | ~0.5k | Dokument-Sync (Content-Store-Anbindung) |
| `tenancy` | ~0.2k | Mandanten / Org-Membership-Guard (`/tenancy/`) |
| `accounts` | ~0.2k | Auth (allauth + OIDC), Root-URLs |

Weitere URL-Mounts: `billing/modules/` (`django_module_shop`), `oidc/`,
`api/schema/` + `api/docs/` (DRF Spectacular / Swagger), `metrics/` + `metrics/prometheus/`.

## Settings-Module (`config/settings/`)
`base.py` · `production.py` · `test.py` · `build.py`. Default Test: `config.settings.test`
(in `pyproject.toml` gepinnt). Prod: `config.settings.production`.

## Lokal hochfahren & testen

```bash
cd ~/github/research-hub
git fetch origin && git status -sb            # main = origin/main? clean?

# App-Stack (Django + Celery + Postgres/pgvector), Port 8098
docker compose -f docker/docker-compose.yml up -d
curl http://127.0.0.1:8098/healthz/

# Tests (KEIN Makefile). Test-Postgres via Compose auf 127.0.0.1:5439, dann pytest.
docker compose -f docker/docker-compose.test.yml up -d
DJANGO_SETTINGS_MODULE=config.settings.test pytest      # pyproject pinnt das Modul bereits
docker compose -f docker/docker-compose.test.yml down
```

> Kein rohes `pytest` ohne lebendes Test-Postgres — sonst `OperationalError` (≠ Code-Defekt).
> Test-DB-Defaults zeigen auf erreichbares TCP `127.0.0.1:5439` (PR #23), nicht auf den Unix-Socket der Lead-Dev-Maschine.

## Arbeitsregeln (repo-spezifisch)

- **Direkt-Commits auf `main` sind blockiert** (`main-tree-guard`, platform:ADR-233).
  Editierende Arbeit → Feature-Branch / Worktree, Merge nur über PR:
  `git worktree add /tmp/<slug> -b <branch> origin/main`.
- **Nach `git switch`/`checkout` vor jedem Edit `git branch --show-current` bestätigen.**
- Commits: `[feat|fix|refactor|docs|test|chore](scope): description`.
- Tests: `test_should_{expected_behavior}`. ADR-058-Marker (`f1 f3 a2 a6 u3`) registriert in `pyproject.toml`.
- Lint: `ruff` (line-length 100, py312; `select = E,F,I,UP,B`).
- **Issue #26 (Infra-Drift) NICHT hier fixen** — platform-Scope (`shared-ci-tag-stale`), gehört in `/ci-green-program`.

## Bekannte Stolperfallen für Agenten

- `.windsurf/` (Rules + Workflows) ist **`.gitignore`'d + symlinked** → in einem frischen Clone nicht vorhanden. Diese `CLAUDE.md` ist die getrackte SSoT.
- **Zwei `Dockerfile` mit klaren Rollen** (Banner am Dateikopf): **root `./Dockerfile` = kanonisch Prod/CI** (shared-ci `_deploy-unified`, braucht `PROJECT_PAT`-BuildKit-Secret); **`docker/Dockerfile` = nur lokaler Dev-Stack** (`docker/docker-compose.yml`). Beim Anpassen die richtige erwischen.
