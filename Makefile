# research-hub — Developer Makefile
#
# Repo hatte zuvor kein Makefile (ruff/pytest liefen direkt über pip/CI-YAML).
# Dieser Makefile enthält bewusst NUR die Klickdummy-Targets (platform:ADR-211)
# — keine Nachbildung der bestehenden CI-Pipeline, um Scope klein zu halten.

.PHONY: klickdummy klickdummy-install klickdummy-i1 klickdummy-i2 klickdummy-i3 klickdummy-sitemap

PYTHON := python3

# =============================================================================
# KLICKDUMMY (platform:ADR-211) — ZENTRAL via iil-klickdummy
# =============================================================================
KLICKDUMMY_VENV := .venv-klickdummy
KLICKDUMMIES    := klickdummy/research-workflow/screens-spec.yaml:klickdummy/research-workflow/screens-spec.schema.json

klickdummy-install: ## Einmalig: venv + zentrales iil-klickdummy
	@$(PYTHON) -m venv $(KLICKDUMMY_VENV) --clear 2>/dev/null || $(PYTHON) -m venv $(KLICKDUMMY_VENV)
	@$(KLICKDUMMY_VENV)/bin/pip install --quiet "iil-klickdummy @ git+https://github.com/iilgmbh/iil-klickdummy.git@main"
	@echo "✓ iil-klickdummy installiert"

klickdummy: klickdummy-i1 klickdummy-i2 klickdummy-i3 ## ADR-211 I1–I3 (zentrale Checks)

klickdummy-i1: ## I1 Spec-first — Spec gegen JSON-Schema (zentral)
	@$(KLICKDUMMY_VENV)/bin/klickdummy-i1 $(KLICKDUMMIES)

klickdummy-i2: ## I2 Prod-Sicherheit — genau eine class deklariert (zentral)
	@$(KLICKDUMMY_VENV)/bin/klickdummy-i2 $(KLICKDUMMIES)

klickdummy-i3: ## I3 Off-Ramp — sunset/Status (zentral)
	@$(KLICKDUMMY_VENV)/bin/klickdummy-i3 $(KLICKDUMMIES)

klickdummy-sitemap: ## KD-Sitemap + kd-tree.json neu generieren
	@$(KLICKDUMMY_VENV)/bin/klickdummy-gen-sitemap . research-hub:ADR-001 research-hub
