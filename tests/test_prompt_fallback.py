"""Tests for the single-source seed-YAML fallback renderer (A4)."""

from config.prompt_fallback import render_seed_messages


def test_should_render_deep_analysis_with_system_and_user_from_seed():
    messages = render_seed_messages(
        "research-hub.research.deep-analysis",
        query="Klimawandel",
        summary="Zusammenfassung X",
        findings_text="- Finding A",
        sources_text="[1] Quelle",
        source_count=1,
        lang_name="English",
    )
    assert messages is not None
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user"]  # YAML carries both templates
    user = messages[1]["content"]
    # rendered from the caller's context, not a hardcoded copy
    assert "Klimawandel" in user
    assert "Zusammenfassung X" in user
    assert "auf English" in user
    # section structure comes from the canonical YAML
    for header in ("Kernaussagen", "Wissenslücken", "Handlungsempfehlungen"):
        assert header in user


def test_should_apply_yaml_default_when_var_missing():
    messages = render_seed_messages(
        "research-hub.research.deep-analysis",
        query="q",
        summary="s",
        findings_text="f",
        sources_text="src",
        source_count=0,
    )
    assert messages is not None
    # lang_name default ("Deutsch") from the YAML defaults block
    assert "auf Deutsch" in messages[1]["content"]


def test_should_render_knowledge_enrich_user_message():
    messages = render_seed_messages(
        "research-hub.knowledge.enrich",
        title="Docker Guide",
        category="DevOps",
        text="Lorem ipsum",
    )
    assert messages is not None
    user = messages[-1]["content"]
    assert "Docker Guide" in user
    assert "DevOps" in user
    assert "Lorem ipsum" in user
    assert '"summary"' in user  # JSON response contract from the YAML


def test_should_return_none_for_unknown_action():
    assert render_seed_messages("research-hub.research.does-not-exist", foo="bar") is None
