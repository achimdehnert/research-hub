# research-hub

AI-Research- & World-Building-Plattform (Epochen, Orte, Namen) — [research.iil.pet](https://research.iil.pet)

Built on `iil-researchfw` PyPI package.

> **Agenten/Details:** [`CLAUDE.md`](CLAUDE.md) ist die Single Source of Truth
> (Apps-Map, Ports, Health-Semantik, Test-/Branch-Regeln). Bei Konflikt gilt
> **Code > CLAUDE.md > alles andere.**

## Stack

- Django 5 + HTMX
- PostgreSQL 16 + pgvector
- Celery + Redis
- iil-researchfw

## Lokal hochfahren

```bash
docker compose -f docker/docker-compose.yml up -d
curl http://127.0.0.1:8098/healthz/
```

Tests: siehe [`CLAUDE.md`](CLAUDE.md) („Lokal hochfahren & testen").

## Deployment

Hetzner: `88.198.191.108` → `research.iil.pet`
# ADR-156 compliance trigger
