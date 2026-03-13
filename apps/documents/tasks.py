"""Celery tasks for Paperless-ngx document sync (ADR-144)."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="documents.sync_paperless")
def sync_paperless_documents(incremental: bool = True) -> dict:
    """Sync documents from Paperless-ngx into DocumentMetadata.

    Args:
        incremental: If True, only sync documents modified in the last 24h.
                     If False, full sync of all documents.

    Returns:
        Dict with sync result counts.
    """
    from .services import sync_all_documents

    modified_after = None
    if incremental:
        modified_after = timezone.now() - timezone.timedelta(days=1)

    return sync_all_documents(modified_after=modified_after)
