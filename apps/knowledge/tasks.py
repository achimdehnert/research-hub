"""Celery tasks for Outline → research-hub sync (ADR-145).

Phase 12: content-hash skip, exponential backoff, rate limiting.
Uses async_to_sync pattern for Celery worker context (ADR-062).
AI enrichment via aifw action code `knowledge.enrich` (M2, ADR-095).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)

ACTION_ENRICH = "knowledge.enrich"


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="knowledge.sync_document",
)
def sync_knowledge_document_task(self, payload: dict[str, Any]) -> str:
    """Sync a document from Outline webhook payload to KnowledgeDocument.

    Called on documents.create, documents.update, documents.publish events.
    """
    from apps.knowledge.services import sync_document_from_outline

    try:
        doc = sync_document_from_outline(payload)
        # Chain AI enrichment only if content changed
        if getattr(doc, "_content_changed", True):
            enrich_knowledge_document_task.delay(doc.pk)
        return f"synced: {doc.title} (id={doc.pk})"
    except Exception as exc:
        logger.exception("sync_knowledge_document_task failed")
        raise self.retry(exc=exc) from exc


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="knowledge.delete_document",
)
def delete_knowledge_document_task(self, outline_id: str) -> str:
    """Soft-delete a KnowledgeDocument when deleted/archived in Outline."""
    from apps.knowledge.services import soft_delete_document

    try:
        deleted = soft_delete_document(outline_id)
        return f"deleted: {outline_id}" if deleted else f"not found: {outline_id}"
    except Exception as exc:
        logger.exception("delete_knowledge_document_task failed")
        raise self.retry(exc=exc) from exc


@shared_task(
    bind=True,
    max_retries=3,
    name="knowledge.enrich_document",
    rate_limit="10/m",
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
)
def enrich_knowledge_document_task(self, doc_pk: int) -> str:
    """AI-enrich a KnowledgeDocument via aifw (ADR-145 Phase 10).

    Generates summary + keywords using action code `knowledge.enrich`.
    Uses sync_completion (Celery worker context, ADR-062).
    """
    import aifw

    from apps.knowledge.models import EnrichmentStatus, KnowledgeDocument
    from apps.knowledge.services import (
        mark_enrichment_complete,
        mark_enrichment_failed,
    )

    try:
        doc = KnowledgeDocument.objects.get(pk=doc_pk, deleted_at__isnull=True)
    except KnowledgeDocument.DoesNotExist:
        return f"not found: pk={doc_pk}"

    # Skip if already enriched and text unchanged
    if doc.enrichment_status == EnrichmentStatus.ENRICHED:
        return f"already enriched: {doc.title}"

    # Truncate text for prompt (max ~6000 chars)
    text = doc.text[:6000]

    # Prompt resolution (ADR-146): DB first, else the canonical seed YAML.
    # No hand-maintained inline copy — see config.prompt_fallback.
    prompt_context = dict(
        title=doc.title,
        category=doc.get_category_display(),
        text=text,
    )
    messages = None
    try:
        from promptfw.contrib.django import render_prompt as db_render_prompt

        messages = db_render_prompt("research-hub.knowledge.enrich", **prompt_context)
    except Exception:
        pass  # fall through to YAML fallback

    if not messages:
        from config.prompt_fallback import render_seed_messages

        messages = render_seed_messages("research-hub.knowledge.enrich", **prompt_context)
    if not messages:
        mark_enrichment_failed(doc, "No prompt template available")
        return f"no prompt: {doc.title}"

    try:
        result = aifw.sync_completion(
            action_code=ACTION_ENRICH,
            messages=messages,
        )
        content = (result.content or "").strip()

        # Parse JSON response
        parsed = json.loads(content)
        summary = parsed.get("summary", "")
        keywords = parsed.get("keywords", [])

        if not summary:
            mark_enrichment_failed(doc, "Empty summary from AI")
            return f"empty summary: {doc.title}"

        mark_enrichment_complete(doc, summary, keywords)
        return f"enriched: {doc.title} ({len(keywords)} keywords)"

    except json.JSONDecodeError as exc:
        mark_enrichment_failed(doc, f"JSON parse error: {exc}")
        logger.warning(
            "Enrichment JSON parse failed for %s: %s",
            doc.title,
            content[:200],
        )
        raise
    except Exception as exc:
        mark_enrichment_failed(doc, str(exc))
        logger.exception("enrich_knowledge_document_task failed")
        raise
