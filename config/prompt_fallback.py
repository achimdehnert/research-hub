"""Offline fallback prompt rendering from the canonical seed YAML.

Single source of truth for fallback prompts: ``prompts/research-hub-seed.yaml``
— the same artifact that seeds the promptfw DB. ``promptfw.render_prompt``
resolves DB-first; when that misses (and ``PROMPTFW_FILE_FALLBACK`` is off),
callers fall back here instead of carrying their own hand-maintained inline
copy that silently drifted from the YAML.

Returns the same chat-message shape as ``promptfw.render_prompt``:
    [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from jinja2 import Environment

_SEED_PATH = Path(settings.BASE_DIR) / "prompts" / "research-hub-seed.yaml"
# autoescape off: prompts are plain LLM text, not HTML — escaping would corrupt them.
_env = Environment(autoescape=False)  # nosec B701


@lru_cache(maxsize=1)
def _load_seed() -> dict[str, dict]:
    """Parse the seed YAML into an ``action_code -> entry`` map (cached)."""
    with open(_SEED_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {p["action_code"]: p for p in data.get("prompts", []) if p.get("action_code")}


def render_seed_messages(action_code: str, **context: Any) -> list[dict[str, str]] | None:
    """Render the seed entry for ``action_code`` into chat messages.

    Merges the entry's ``defaults`` with ``context`` (caller wins), mirroring
    ``render_prompt``. Returns ``None`` if the YAML or the entry is missing, so
    the caller can degrade gracefully.
    """
    try:
        entry = _load_seed().get(action_code)
    except (OSError, yaml.YAMLError):
        return None
    if not entry:
        return None

    merged = {**entry.get("defaults", {}), **context}
    messages: list[dict[str, str]] = []

    system_tpl = entry.get("system_template")
    if system_tpl:
        messages.append(
            {"role": "system", "content": _env.from_string(system_tpl).render(**merged).strip()}
        )
    user_tpl = entry.get("user_template", "")
    messages.append(
        {"role": "user", "content": _env.from_string(user_tpl).render(**merged).strip()}
    )
    return messages
