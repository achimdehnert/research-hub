# AGENT_HANDOVER — research-hub

## ⚡ Aktueller Stand (2026-06-12, ~16:10)

**Aktiver Branch:** `main` (clean, alle Feature-PRs gemerged)

**🚨 OFFENER PROD-INCIDENT — wartet auf User-Freigabe:**
**research.iil.pet ist DOWN (HTTP 502).** Deploy-Run 27427137520: Build+Push grün,
Production-Job Exit 10, **automatischer Rollback ebenfalls fehlgeschlagen**.

**Root Cause (verifiziert):** Image-Namens-Mismatch —
- shared-ci pusht: `ghcr.io/achimdehnert/research-hub:main-7f6382a` (existiert ✅)
- `docker-compose.prod.yml:57+95` erwartet: `ghcr.io/.../research-hub/research-hub-web:${IMAGE_TAG}` (existiert NICHT in GHCR)
- Deploy #7 (2026-06-10) scheiterte am identischen Fehler → Prod evtl. schon seit 10.06. down (unverifiziert — Betterstack prüfen)

**Nächster Schritt (vorgeschlagen, NICHT freigegeben):**
```bash
# 1. docker-compose.prod.yml Zeilen 57+95 ändern auf:
#    image: ghcr.io/${GHCR_OWNER:-achimdehnert}/${GHCR_REPO:-research-hub}:${IMAGE_TAG:-latest}
# 2. PR + Merge → Deploy läuft automatisch und zieht das existierende Image main-7f6382a
# Risiko: Host-Warnung "COMPOSE_PROJECT_NAME running='137-hub' expected='research-hub'"
#         → mögliche Port-Konflikte mit Orphan-Containern; SSH-Inspektion war
#         vom Permission-Classifier geblockt (devuser@88.198.191.108, read-only nötig)
```

**Was diese Session erledigt hat:**
- PR #8 (gemerged): P1 Security/Cache (Redis-CACHES db1, Sessions cached_db,
  Metrics-Query-Param-Token entfernt, Webhook-Ratelimit 120/min, DEBUG-Default
  False, HSTS, Healthcheck-Fix) + P2 (Delete-UI mit Soft-Delete-Kaskade,
  Pagination 24/50, async summary_reformat via Celery+Cache-Polling, N+1-Fixes,
  org_create-Validierung). Tests 66 → 96.
- PR #9 (gemerged): ruff format base.py (Deploy-Format-Gate) + tote Legacy-URL-
  Aliasse entfernt (project-detail-legacy war unerreichbar) + verwaistes Template.
- PR #10 (gemerged): **Deploy-Secrets explizit mappen** — `secrets: inherit`
  reicht cross-owner (achimdehnert-Repo → iilgmbh/shared-ci) KEINE Secrets durch.
  Build sah `PROJECT_PAT=` leer. Betrifft vermutlich ALLE per Ref-Sweep
  umgestellten Repos! (🌀 Memory: shared-ci-cross-owner-secrets)
- Transienter GHA-Cache-Fehler (`error writing layer blob: not_found`) → via
  `gh run rerun --failed` gelöst.

**Offener Punkt aus session-ende:** Outline-MCP war in dieser Session nicht
verbunden → /knowledge-capture konnte die Lesson „secrets:inherit cross-owner"
NICHT nach Outline schreiben. Nächste Session mit Outline-Tools:
`create_lesson("2026-06-12: secrets:inherit reicht cross-owner keine Secrets durch", …)`
— Inhalt steht im 🌀-Memory `shared-ci-cross-owner-secrets` + pgvector
`error:research-hub:20260612-secrets-inherit`.

**TODO aus session-ende (Issue-Erstellung vom Permission-Classifier geblockt):**
```bash
# 1. Docu-Update (platform-Repo, Phase 1b — Trigger: neue apps/tenancy/forms.py + PRs #8/#9/#10)
gh issue create -R achimdehnert/platform --title "[docu-update] research-hub — neue Module + P1/P2-Features ohne Doku-Nachzug" --label documentation --label docu-update --label automated --body "CHANGELOG für #8/#9/#10, README (CACHE_URL/HSTS/Delete-UI), Outline-Lesson secrets:inherit nachtragen"
# 2. Template-Drift (research-hub, Phase 1c — 2 Errors, vorbestehend)
gh issue create -R achimdehnert/research-hub --title "Template-Drift: root requirements.txt fehlt + HEALTHCHECK im Dockerfile (ADR-078)" --body "drift_check.py errors 2026-06-12; NICHT während des Prod-Incidents fixen (Deploy-Pfad)"
```

**Lokale Test-Umgebung (neu eingerichtet, git-ignoriert):**
`.venv` mit `--system-site-packages` + `wheels/iil_content_store-*.whl` +
lokale Editables aus `~/github/platform/_ARCHIVED/packages/`. Testlauf:
```bash
SECRET_KEY=x TEST_DB_HOST=127.0.0.1 CONTENT_STORE_DB_HOST=127.0.0.1 \
CONTENT_STORE_DB_PORT=5434 CONTENT_STORE_DB_USER=dehnert \
.venv/bin/python -m pytest -q
```
