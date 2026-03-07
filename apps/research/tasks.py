"""Celery tasks for async research execution."""
from __future__ import annotations

import asyncio
import logging

from config.celery import app
from apps.research.models import ResearchProject
from apps.research.services import ResearchProjectService

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3)
def run_research_task(self, project_id: int) -> None:
    """Async-safe Celery task for research execution."""
    try:
        project = ResearchProject.objects.get(pk=project_id)
        ResearchProject.objects.filter(pk=project_id).update(status="running")
        service = ResearchProjectService()
        asyncio.run(service.run_research(project))
    except ResearchProject.DoesNotExist:
        logger.error("ResearchProject %s not found", project_id)
    except Exception as exc:
        logger.exception("Research task failed for project %s", project_id)
        ResearchProject.objects.filter(pk=project_id).update(status="error")
        raise self.retry(exc=exc, countdown=60)
