---
description: Schneller Produktions-Fix für research-hub
---

# Hotfix — research-hub

## 1. Problem identifizieren
// turbo
```
MCP: mcp6_docker_manage → container_logs(container_id="research_hub_web", host="88.198.191.108", lines=50)
```

## 2. Fix implementieren
- Minimaler Fix, kein Refactoring
- Nur betroffene Datei(en) ändern

## 3. Test lokal
// turbo
```bash
pytest tests/ -x -q --tb=short
```

## 4. Commit + Push
```bash
git add -A && git commit -m "fix: [BESCHREIBUNG]" && git push origin main
```

## 5. Deploy (wenn CD nicht automatisch)
```
MCP: mcp6_ssh_manage → exec(
  host="88.198.191.108",
  command="cd /opt/research-hub && docker compose -f docker-compose.prod.yml pull research-hub-web && docker compose -f docker-compose.prod.yml up -d --no-deps --force-recreate research-hub-web"
)
```

## 6. Verify
// turbo
```
MCP: mcp6_ssh_manage → http_check(url="http://127.0.0.1:8098/healthz/", host="88.198.191.108")
```
