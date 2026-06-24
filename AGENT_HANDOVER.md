# AGENT_HANDOVER · research-hub

> Führende Quelle für „was steht als nächstes an?". Beim Session-Ende aktualisieren
> (`/session-ende`). Der Session-Start-Hook liest die Sektion `## Prioritäten`.
> AI-Research-Plattform (Django + Celery + pgvector). Prod: https://research.iil.pet
> Server `88.198.191.108`, Compose-Service `research-hub-web`, Port 8098.

## Stand 2026-06-23 — synced, grün, bereit für neue Aufgaben

**Aktueller Zustand:** `main` = `origin/main` (`1268482`), Working-Tree clean.
Letzter Deploy grün (Run 28023059082, success). Keine offenen PRs/Issues.

**Diese Session erledigt:**
- Lokalen `main` mit `origin/main` synchronisiert — war 192 voraus / 302 hinterher,
  alle 192 Lokal-Commits waren als squash-PRs auf origin dupliziert (`git cherry`
  verifiziert), daher `reset --hard origin/main` ohne Verlust.
- `NEXT.md` aus stale (2026-06-12, zeigte auf #6) auf realen Stand gefrischt (PR #20).
- Diese `AGENT_HANDOVER.md` angelegt, damit der Session-Start nicht mehr auf den
  git-log-Fallback zurückfällt.
- Vier verwaiste `repo-session`-Worktrees abgeschlossener PRs (#7, #16–#18)
  entfernt; nur noch der Haupt-Tree existiert.

**Zuletzt gemergt (heute):**
- #16 Tenant-Isolation & Daten-Integrität härten (#5–#9)
- #17 Cross-Org-IDOR-Guard (Tenant-Membership-Middleware + Test)
- #18 `docker/secrets/*` aus Git-Tracking genommen (ADR-045)
- #19 shared-ci `_deploy-unified` v1.0.6 → v1.0.8 (GHCR_TOKEN-Durchreichung)

## Prioritäten

> Aktuell **keine angefangene Arbeit** zum Fortsetzen — Repo ist bereit für neue Aufgaben.
> Reihenfolge ist Vorschlag, kein verbindlicher Backlog.

1. Kein offener Backlog — neues Thema/Issue definieren, dann passend routen.
2. Optional auf frisch syncedem Stand: `/teste-repo` oder `/repo-health-check` fahren.

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
