"""Celery tasks for Outline → research-hub sync (ADR-145, Review-Fix K2).

Uses async_to_sync pattern for Celery worker context (ADR-062).
"""
from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


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
