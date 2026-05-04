# Project Facts: research-hub

> Auto-generiert von `platform/.github/scripts/push_project_facts.py`
> Letzte Aktualisierung: 2026-05-04 — bei Änderungen: `platform/gen-project-facts.yml` triggern

## Meta

- **Type**: `django`
- **GitHub**: `https://github.com/achimdehnert/research-hub`
- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)

## Lokale Umgebung (Dev Desktop — adehnert)

- **Pfad**: `~/CascadeProjects/research-hub` → `$GITHUB_DIR` = `~/CascadeProjects`
- **src_root**: `./` (root) — `manage.py` liegt dort
- **pythonpath**: `./`
- **Venv**: `~/CascadeProjects/research-hub/.venv/bin/python`
- **MCP aktiv**: `mcp0_` = github · `mcp1_` = orchestrator

## Settings

- **Prod-Modul**: `config.settings.production`
- **Test-Modul**: `config.settings.test`
- **Testpfad**: `tests/`

## Stack

- **Django**: `5.x`
- **Python**: `3.12`
- **PostgreSQL**: `16`
- **HTMX installiert**: nein
- **HTMX-Detection**: `request.headers.get("HX-Request") == "true"`


## Apps

- `accounts`
- `documents`
- `knowledge`
- `research`
- `tenancy`

## Infrastruktur

- **Prod-URL**: `research.iil.pet`
- **Staging-URL**: `staging.research.iil.pet`
- **Port**: `8104`
- **Health-Endpoint**: `/livez/`
- **DB-Name**: `research_hub`

## System (Hetzner Server)

- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:
  ```bash
  ssh root@localhost "apt-get install -y <package>"
  ```
