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
        return result

    async def _deep_analyze(
        self,
        project: ResearchProject,
        result: ResearchResult,
    ) -> str:
        """Stufe 2: Tiefenanalyse via aifw action code.

        Nimmt die Ergebnisse aus Stufe 1 (Zusammenfassung,
        Findings, Quellen) und erzeugt eine strukturierte
        Tiefenanalyse.
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

        llm_result = await aifw.completion(
            action_code=ACTION_DEEP_ANALYSIS,
            messages=[{"role": "user", "content": prompt}],
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
