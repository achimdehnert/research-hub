"""Celery tasks for async research execution."""

from __future__ import annotations

import asyncio
import logging

from apps.research.models import ResearchProject
from apps.research.services import ResearchProjectService
from config.celery import app

logger = logging.getLogger(__name__)

REFORMAT_CACHE_TTL = 600  # seconds — reformat results are one-shot, short-lived


@app.task(bind=True, max_retries=3)
def run_research_task(self, project_id: int) -> None:
    """Async-safe Celery task for research execution."""
    try:
        project = ResearchProject.objects.get(pk=project_id)
        ResearchProject.objects.filter(pk=project_id).update(status="running")
        service = ResearchProjectService()
        # request.id is stable across retries of the same task → idempotent run.
        run_token = str(self.request.id or "")
        asyncio.run(service.run_research(project, run_token=run_token))
    except ResearchProject.DoesNotExist:
        logger.error("ResearchProject %s not found", project_id)
    except Exception as exc:
        logger.exception("Research task failed for project %s", project_id)
        ResearchProject.objects.filter(pk=project_id).update(status="error")
        raise self.retry(exc=exc, countdown=60) from exc


def _make_sync_aifw_llm():
    """Sync LLM callable via aifw for TextReformatter."""
    import aifw

    def _call(prompt: str) -> str:
        result = aifw.sync_completion(
            action_code="research.reformat",
            messages=[{"role": "user", "content": prompt}],
        )
        return (result.content or "").strip()

    return _call


@app.task(bind=True, max_retries=0)
def reformat_summary_task(
    self, result_id: int, target_format: str, language: str, cache_key: str
) -> None:
    """Reformat a result summary via LLM; store the outcome under cache_key.

    Falls back to the original summary on any LLM/parsing error — the
    polling endpoint then simply shows the unchanged text.
    """
    from django.core.cache import cache

    from apps.research.models import ResearchResult

    result = ResearchResult.objects.filter(pk=result_id).first()
    if not result or not result.summary:
        cache.set(
            cache_key,
            {"status": "done", "summary": "", "target_format": target_format},
            REFORMAT_CACHE_TTL,
        )
        return

    try:
        from authoringfw.text import ReformatTask, TextReformatter

        reformatter = TextReformatter(llm_fn=_make_sync_aifw_llm())
        reformat_result = reformatter.reformat(
            ReformatTask(
                source_text=result.summary,
                target_format=target_format,
                language=language or "de",
            )
        )
        reformatted = reformat_result.content
    except Exception:
        logger.exception("Summary reformat failed for result %s", result_id)
        reformatted = result.summary

    cache.set(
        cache_key,
        {"status": "done", "summary": reformatted, "target_format": target_format},
        REFORMAT_CACHE_TTL,
    )
