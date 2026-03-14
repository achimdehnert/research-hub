"""Celery tasks for Outline → research-hub sync (ADR-145, Review-Fix K2).

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
        # Chain AI enrichment (Phase 10)
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
    max_retries=2,
    default_retry_delay=60,
    name="knowledge.enrich_document",
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

    prompt = f"""Analysiere das folgende technische Dokument und erstelle:

1. Eine prägnante deutsche Zusammenfassung (2-4 Sätze)
2. Eine Liste von 3-8 Keywords (englisch, lowercase)

Dokument-Titel: {doc.title}
Kategorie: {doc.get_category_display()}

---
{text}
---

Antworte EXAKT in diesem JSON-Format:
{{"summary": "...", "keywords": ["keyword1", "keyword2", ...]}}"""

    try:
        result = aifw.sync_completion(
            action_code=ACTION_ENRICH,
            messages=[{"role": "user", "content": prompt}],
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
            doc.title, content[:200],
        )
        raise self.retry(exc=exc) from exc
    except Exception as exc:
        mark_enrichment_failed(doc, str(exc))
        logger.exception("enrich_knowledge_document_task failed")
        raise self.retry(exc=exc) from exc
