# research-hub

Django research platform — [research.iil.pet](https://research.iil.pet)

Built on `iil-researchfw` PyPI package.

## Stack

- Django 5 + HTMX
- PostgreSQL 16 + pgvector
- Celery + Redis
- iil-researchfw

## Lokal starten & testen

```bash
docker compose -f docker/docker-compose.yml up -d        # App-Stack, Port 8098
curl http://127.0.0.1:8098/healthz/

docker compose -f docker/docker-compose.test.yml up -d   # Test-Postgres (127.0.0.1:5439)
DJANGO_SETTINGS_MODULE=config.settings.test pytest
```

## Deployment

Hetzner: `88.198.191.108` → `research.iil.pet`

## Für Agenten / Details

**Single Source of Truth ist [`CLAUDE.md`](CLAUDE.md)** — kanonische Fakten (Ports, Health-Endpoints,
content_store-DB), Arbeitsregeln und bekannte Stolperfallen. Stand/Backlog: `AGENT_HANDOVER.md`.
