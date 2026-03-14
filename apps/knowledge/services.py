"""Knowledge service layer (ADR-041: views → services → models).

Handles CRUD for KnowledgeDocument, called from webhook view and Celery tasks.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.knowledge.models import (
    EnrichmentStatus,
    KnowledgeCategory,
    KnowledgeDocument,
)

logger = logging.getLogger(__name__)

# Map Outline collection IDs to categories
COLLECTION_CATEGORY_MAP: dict[str, KnowledgeCategory] = {
    "a67c9777-3bc3-401a-9de3-91f0cc6c56d9": KnowledgeCategory.RUNBOOK,
    "04064c28-a847-4bec-9bc3-a74d5e1012a2": KnowledgeCategory.CONCEPT,
    "db8291c2-f135-4834-878e-224db5673ab6": KnowledgeCategory.LESSON,
    "21678f65-80d7-4594-a1d2-660c8770acfa": KnowledgeCategory.ADR_DRAFT,
    "69d7d88b-7f15-447e-8da5-efc500f8bd29": KnowledgeCategory.HUB_DOC,
    "cf12fd43-4b14-4e1f-9603-dd7cb124071f": KnowledgeCategory.ADR_MIRROR,
}


def sync_document_from_outline(payload: dict[str, Any]) -> KnowledgeDocument:
    """Create or update a KnowledgeDocument from an Outline webhook payload.

    Args:
        payload: Outline webhook event data containing document info.

    Returns:
        The created or updated KnowledgeDocument instance.
    """
    doc_data = payload.get("data", {})
    doc_id = doc_data.get("id")
    if not doc_id:
        raise ValueError("Missing document id in webhook payload")

    collection_id = doc_data.get("collectionId", "")
    category = COLLECTION_CATEGORY_MAP.get(
        collection_id, KnowledgeCategory.RUNBOOK
    )

    outline_updated = doc_data.get("updatedAt")
    outline_updated_dt = None
    if outline_updated:
        try:
            outline_updated_dt = datetime.fromisoformat(
                outline_updated.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            logger.warning("Could not parse updatedAt: %s", outline_updated)

    defaults = {
        "title": doc_data.get("title", "Untitled"),
        "text": doc_data.get("text", ""),
        "outline_url": doc_data.get("url", ""),
        "collection_id": collection_id or None,
        "category": category,
        "outline_updated_at": outline_updated_dt,
    }

    doc, created = KnowledgeDocument.objects.update_or_create(
        outline_id=doc_id,
        defaults=defaults,
    )

    action = "created" if created else "updated"
    logger.info(
        "KnowledgeDocument %s: %s (outline_id=%s)", action, doc.title, doc_id,
    )
    return doc


def soft_delete_document(outline_id: str) -> bool:
    """Soft-delete a KnowledgeDocument by Outline ID.

    Returns:
        True if document was found and soft-deleted, False otherwise.
    """
    try:
        doc = KnowledgeDocument.objects.get(
            outline_id=outline_id, deleted_at__isnull=True,
        )
        doc.deleted_at = timezone.now()
        doc.save(update_fields=["deleted_at", "updated_at"])
        logger.info(
            "KnowledgeDocument soft-deleted: %s (outline_id=%s)",
            doc.title, outline_id,
        )
        return True
    except KnowledgeDocument.DoesNotExist:
        logger.warning(
            "KnowledgeDocument not found for soft-delete: outline_id=%s",
            outline_id,
        )
        return False


def mark_enrichment_complete(
    doc: KnowledgeDocument,
    summary: str,
    keywords: list[str],
) -> None:
    """Update document with AI enrichment results."""
    doc.summary = summary
    doc.keywords = keywords
    doc.enrichment_status = EnrichmentStatus.ENRICHED
    doc.enriched_at = timezone.now()
    doc.save(update_fields=[
        "summary", "keywords", "enrichment_status", "enriched_at", "updated_at",
    ])
    logger.info("KnowledgeDocument enriched: %s", doc.title)


def mark_enrichment_failed(doc: KnowledgeDocument, error: str) -> None:
    """Mark enrichment as failed."""
    doc.enrichment_status = EnrichmentStatus.FAILED
    doc.save(update_fields=["enrichment_status", "updated_at"])
    logger.error("KnowledgeDocument enrichment failed: %s — %s", doc.title, error)
