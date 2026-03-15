---
description: Deploy research-hub to production
---

# Deploy research-hub

## Pre-Flight
1. Verify main branch is clean: `git status`
2. Run tests locally: `pytest tests/ -x -q`
3. Check current prod health:
   ```
   MCP: mcp6_docker_manage → container_status(container_id="research_hub_web", host="88.198.191.108")
   ```

## Deploy (CD Pipeline)
// turbo
4. Push to main triggers CD automatically:
   ```bash
   git push origin main
   ```
5. Monitor CD build:
   ```bash
   GITHUB_TOKEN="" gh run list --repo achimdehnert/research-hub --limit 1
   ```

## Manual Deploy (if CD fails)
6. SSH to server and pull + restart:
   ```
   MCP: mcp6_ssh_manage → exec(
     host="88.198.191.108",
     command="cd /opt/research-hub && docker compose -f docker-compose.prod.yml pull research-hub-web && docker compose -f docker-compose.prod.yml up -d --no-deps --force-recreate research-hub-web"
   )
   ```

## Post-Deploy Verification
// turbo
7. Health check:
   ```
   MCP: mcp6_ssh_manage → http_check(url="http://127.0.0.1:8098/healthz/", host="88.198.191.108")
   ```
8. Check container logs for errors:
   ```
   MCP: mcp6_docker_manage → container_logs(container_id="research_hub_web", host="88.198.191.108", lines=20)
   ```

## Key Info
- **Server**: 88.198.191.108
- **Compose**: /opt/research-hub/docker-compose.prod.yml
- **Port**: 8098 (internal)
- **Domain**: https://research.iil.pet
- **GHCR Image**: ghcr.io/achimdehnert/research-hub/research-hub-web:latest
