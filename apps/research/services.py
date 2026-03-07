"""Research service layer — wraps iil-researchfw."""
from __future__ import annotations

import logging
from typing import Any

from iil_researchfw import AcademicSearchService, BraveSearchService, ResearchService
from iil_researchfw.core.models import ResearchOutput

from apps.research.models import ResearchProject, ResearchResult

logger = logging.getLogger(__name__)


class ResearchProjectService:
    """Business logic for ResearchProject — wraps iil-researchfw."""

    def _build_service(self, project: ResearchProject) -> ResearchService:
        import os
        brave_key = os.environ.get("BRAVE_API_KEY", "")
        rtype = project.research_type
        use_web = rtype in ("web", "combined", "fact_check")
        use_academic = rtype in ("academic", "combined")
        return ResearchService(
            web_search=BraveSearchService(api_key=brave_key) if (brave_key and use_web) else None,
            academic_search=AcademicSearchService() if use_academic else None,
        )

    async def run_research(self, project: ResearchProject) -> ResearchResult:
        """Execute research for a project and persist results."""
        service = self._build_service(project)
        max_sources = ResearchProject.DEPTH_TO_SOURCES.get(project.depth, 15)
        options: dict[str, Any] = {
            "max_sources": max_sources,
            "language": project.language or "de",
        }
        if project.research_type == "fact_check":
            output: ResearchOutput = await service.fact_check(project.query, sources=max_sources)
        else:
            output = await service.research(query=project.query, options=options)

        result = await ResearchResult.objects.acreate(
            project=project,
            query=project.query,
            sources_json=[s.model_dump() for s in output.sources],
            findings_json=[f.model_dump() for f in output.findings],
            summary=output.summary or "",
        )
        await ResearchProject.objects.filter(pk=project.pk).aupdate(
            status="done" if output.success else "error"
        )
        return result

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
