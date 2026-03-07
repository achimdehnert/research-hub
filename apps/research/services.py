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

    def _build_service(self) -> ResearchService:
        import os
        brave_key = os.environ.get("BRAVE_API_KEY", "")
        return ResearchService(
            web_search=BraveSearchService(api_key=brave_key) if brave_key else None,
            academic_search=AcademicSearchService(),
        )

    async def run_research(self, project: ResearchProject) -> ResearchResult:
        """Execute research for a project and persist results."""
        service = self._build_service()
        output: ResearchOutput = await service.research(
            query=project.query,
            options={"max_sources": 15},
        )
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
        self, user: Any, name: str, query: str, description: str = ""
    ) -> ResearchProject:
        return ResearchProject.objects.create(
            user=user, name=name, query=query, description=description
        )
