"""Research service layer — wraps iil-researchfw.

All LLM calls go through **aifw** (action-code routing, model
management, secret resolution).  No raw litellm / env-var access
for API keys.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import aifw
from iil_researchfw import (
    AcademicSearchService,
    AISummaryService,
    BraveSearchService,
    ResearchService,
)
from iil_researchfw.core.models import ResearchOutput

from apps.research.models import ResearchProject, ResearchResult

logger = logging.getLogger(__name__)

# aifw action codes (seeded via `manage.py seed_aifw`)
ACTION_SUMMARIZE = "research.summarize"
ACTION_DEEP_ANALYSIS = "research.deep_analysis"


def _make_aifw_llm_fn(action_code: str = ACTION_SUMMARIZE):
    """Return an async LLM callable backed by aifw.

    Matches ``iil_researchfw.core.protocols.LLMCallable``:
        async (prompt, max_tokens, response_format) -> str
    """

    async def _call(
        prompt: str,
        max_tokens: int = 500,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        overrides: dict[str, Any] = {}
        if max_tokens:
            overrides["max_tokens"] = max_tokens
        if response_format:
            overrides["response_format"] = response_format
        result = await aifw.completion(
            action_code=action_code,
            messages=[{"role": "user", "content": prompt}],
            **overrides,
        )
        return result.content or ""

    return _call


def _publish_to_content_store(
    project: ResearchProject,
    result: ResearchResult,
) -> None:
    """Publish research results to content-store (ADR-130).

    Creates/updates ContentItem entries for summary and deep
    analysis so other hubs can access them.
    """
    import hashlib

    try:
        from content_store.models import ContentItem
    except ImportError:
        logger.debug("content_store not available, skipping")
        return

    db = "content_store"
    tenant_id = 0
    ws = project.workspace
    if ws and ws.tenant_id:
        # Use first 8 hex digits of UUID as integer
        tenant_id = int(str(ws.tenant_id).replace("-", "")[:8], 16)

    ref = str(project.public_id)

    # --- Summary ---
    if result.summary:
        sha = hashlib.sha256(
            result.summary.encode(),
        ).hexdigest()
        ContentItem.objects.using(db).update_or_create(
            source="research-hub",
            type="summary",
            ref_id=ref,
            defaults={
                "tenant_id": tenant_id,
                "content": result.summary,
                "sha256": sha,
                "version": 1,
                "meta": {
                    "query": project.query,
                    "language": project.language,
                    "research_type": project.research_type,
                    "depth": project.depth,
                    "source_count": len(
                        result.sources_json or [],
                    ),
                },
                "model_used": "aifw:research.summarize",
                "prompt_key": "",
            },
        )
        logger.info(
            "Published summary to content-store: %s", ref,
        )

    # --- Deep Analysis ---
    if result.deep_analysis:
        sha = hashlib.sha256(
            result.deep_analysis.encode(),
        ).hexdigest()
        ContentItem.objects.using(db).update_or_create(
            source="research-hub",
            type="deep_analysis",
            ref_id=ref,
            defaults={
                "tenant_id": tenant_id,
                "content": result.deep_analysis,
                "sha256": sha,
                "version": 1,
                "meta": {
                    "query": project.query,
                    "language": project.language,
                    "model": (
                        result.deep_analysis_model or ""
                    ),
                },
                "model_used": (
                    result.deep_analysis_model
                    or "aifw:research.deep_analysis"
                ),
                "prompt_key": "",
            },
        )
        logger.info(
            "Published deep_analysis to content-store: %s",
            ref,
        )


class ResearchProjectService:
    """Business logic for ResearchProject — wraps iil-researchfw.

    LLM calls use aifw action codes:
    - ``research.summarize``   → Stufe 1 (Together / Llama)
    - ``research.deep_analysis`` → Stufe 2 (OpenAI / gpt-4.1)
    """

    def _build_service(
        self, project: ResearchProject,
    ) -> ResearchService:
        brave_key = os.environ.get("BRAVE_API_KEY", "")
        rtype = project.research_type
        use_web = rtype in ("web", "combined", "fact_check")
        use_academic = rtype in ("academic", "combined")
        llm_fn = _make_aifw_llm_fn(ACTION_SUMMARIZE)
        return ResearchService(
            web_search=(
                BraveSearchService(api_key=brave_key)
                if (brave_key and use_web) else None
            ),
            academic_search=(
                AcademicSearchService()
                if use_academic else None
            ),
            summary_service=AISummaryService(llm_fn=llm_fn),
        )

    async def run_research(
        self, project: ResearchProject,
    ) -> ResearchResult:
        """Execute research for a project and persist results."""
        service = self._build_service(project)
        max_sources = ResearchProject.DEPTH_TO_SOURCES.get(
            project.depth, 15,
        )
        options: dict[str, Any] = {
            "max_sources": max_sources,
            "language": project.language or "de",
        }
        if project.research_type == "fact_check":
            output: ResearchOutput = await service.fact_check(
                project.query, sources=max_sources,
            )
        else:
            output = await service.research(
                query=project.query,
                options={
                    **options,
                    "summary_style": project.summary_level,
                    "citation_style": project.citation_style,
                },
            )

        result = await ResearchResult.objects.acreate(
            project=project,
            query=project.query,
            sources_json=[
                s.model_dump(mode="json")
                for s in output.sources
            ],
            findings_json=[
                f.model_dump(mode="json")
                for f in output.findings
            ],
            summary=output.summary or "",
        )

        # --- Stufe 2: Tiefenanalyse via aifw ---
        if project.use_deep_analysis and output.success:
            await ResearchProject.objects.filter(
                pk=project.pk,
            ).aupdate(status="analysing")
            try:
                from asgiref.sync import sync_to_async
                config = await sync_to_async(
                    aifw.get_action_config,
                )(ACTION_DEEP_ANALYSIS)
                deep = await self._deep_analyze(
                    project, result,
                )
                model_name = config.get("model", "")
                await ResearchResult.objects.filter(
                    pk=result.pk,
                ).aupdate(
                    deep_analysis=deep,
                    deep_analysis_model=model_name,
                )
            except Exception:
                logger.exception(
                    "Deep analysis failed for %s",
                    project.pk,
                )

        await ResearchProject.objects.filter(
            pk=project.pk,
        ).aupdate(
            status="done" if output.success else "error",
        )

        # --- Publish to content-store (ADR-130) ---
        if output.success:
            try:
                from asgiref.sync import sync_to_async
                # Re-fetch result to get deep_analysis if updated
                fresh = await ResearchResult.objects.filter(
                    pk=result.pk,
                ).afirst()
                await sync_to_async(
                    _publish_to_content_store,
                )(project, fresh or result)
            except Exception:
                logger.exception(
                    "content-store publish failed for %s",
                    project.pk,
                )

        return result

    async def _deep_analyze(
        self,
        project: ResearchProject,
        result: ResearchResult,
    ) -> str:
        """Stufe 2: Tiefenanalyse via aifw action code.

        Resolution order (ADR-146):
          1. DB: promptfw.contrib.django.render_prompt() — cached
          2. Inline: f-string fallback (legacy)
        """
        # Quellen-Kontext aufbauen
        source_lines = []
        for i, s in enumerate(result.sources_json[:30], 1):
            title = s.get("title", "")
            snippet = s.get("snippet", "")
            url = s.get("url", "")
            source_lines.append(
                f"[{i}] {title}\n    {snippet}\n    {url}"
            )
        sources_text = "\n".join(source_lines)

        # Findings-Kontext
        finding_lines = []
        for f in result.findings_json[:20]:
            finding_lines.append(
                f"- {f.get('claim', f.get('text', ''))}"
            )
        findings_text = "\n".join(finding_lines)

        lang = project.language or "de"
        lang_name = {
            "de": "Deutsch", "en": "English",
            "fr": "Français", "es": "Español",
        }.get(lang, lang)

        # 1. Try DB-backed prompt (ADR-146)
        messages = None
        try:
            from promptfw.contrib.django import render_prompt as db_render_prompt

            messages = db_render_prompt(
                "research-hub.research.deep-analysis",
                query=project.query,
                summary=result.summary,
                findings_text=findings_text,
                sources_text=sources_text,
                source_count=len(result.sources_json),
                lang_name=lang_name,
            )
        except Exception:
            pass  # fall through to inline

        # 2. Inline fallback (legacy)
        if not messages:
            prompt = f"""Du bist ein erfahrener Forschungsanalyst.

Du erhältst die Ergebnisse einer Recherche zum Thema:
"{project.query}"

== ZUSAMMENFASSUNG (Stufe 1) ==
{result.summary}

== FINDINGS ==
{findings_text}

== QUELLEN ({len(result.sources_json)}) ==
{sources_text}

Erstelle eine **Tiefenanalyse** auf {lang_name}:

1. **Kernaussagen** — Die 3-5 wichtigsten Erkenntnisse
2. **Analyse** — Bewertung, Widersprüche, \
Stärken/Schwächen der Quellen
3. **Wissenslücken** — Was fehlt, offene Fragen
4. **Methodische Einordnung** — Qualität der Quellenbasis
5. **Handlungsempfehlungen** — Konkrete nächste Schritte

Schreibe in Markdown. Sei analytisch, kritisch, präzise.
"""
            messages = [{"role": "user", "content": prompt}]

        llm_result = await aifw.completion(
            action_code=ACTION_DEEP_ANALYSIS,
            messages=messages,
        )
        return llm_result.content or ""

    def create_project(
        self,
        user: Any,
        name: str,
        query: str,
        description: str = "",
        research_type: str = "combined",
        depth: str = "standard",
        academic_sources: list[str] | None = None,
        language: str = "de",
    ) -> ResearchProject:
        return ResearchProject.objects.create(
            user=user,
            name=name,
            query=query,
            description=description,
            research_type=research_type,
            depth=depth,
            academic_sources=academic_sources or [],
            language=language,
        )
