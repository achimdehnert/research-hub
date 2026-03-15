---
description: Session-Start für research-hub — Kontext laden, Stand prüfen
---

# Session Start — research-hub

## Step 1: Kontext laden
1. Lies `config/settings/base.py` (INSTALLED_APPS, Middleware, OIDC)
2. Lies `config/urls.py` (URL-Routing)
3. Prüfe offene Issues:
   ```bash
   GITHUB_TOKEN="" gh issue list --repo achimdehnert/research-hub --limit 5
   ```

## Step 2: Prod-Status prüfen
// turbo
4. Container-Health:
   ```
   MCP: mcp6_docker_manage → container_status(container_id="research_hub_web", host="88.198.191.108")
   ```

## Step 3: Branch + Git-Status
// turbo
5. ```bash
   git status && git log --oneline -5
   ```

## Key Facts
- **Tech Stack**: Django 5.x, PostgreSQL, Celery, Redis, HTMX
- **Tenancy**: django-tenants (SubdomainTenantMiddleware)
- **Auth**: allauth + authentik OIDC (ADR-142)
- **Knowledge**: Outline Webhook → AI-Enrichment (ADR-145)
- **Server**: 88.198.191.108, Port 8098
- **Domain**: https://research.iil.pet
