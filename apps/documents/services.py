"""Paperless-ngx sync service (ADR-144).

Pulls documents from Paperless REST API and upserts into DocumentMetadata.
Paperless = Source of Truth for files + OCR. research-hub = metadata + AI.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx
from decouple import config as decouple_config
from django.utils import timezone

from .models import DocumentMetadata, DocumentMetadataStatus, PLATFORM_INTERNAL_TENANT_ID

logger = logging.getLogger(__name__)

PAPERLESS_TIMEOUT = 30.0


def _get_paperless_url() -> str:
    return decouple_config("PAPERLESS_URL", default="http://127.0.0.1:8102")


def _get_paperless_headers() -> dict[str, str]:
    token = decouple_config("PAPERLESS_API_TOKEN", default="")
    if not token:
        raise ValueError("PAPERLESS_API_TOKEN not configured")
    return {
        "Authorization": f"Token {token}",
        "Accept": "application/json; version=5",
    }


def fetch_paperless_documents(
    page_size: int = 100,
    modified_after: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch documents from Paperless-ngx API.

    Args:
        page_size: Number of documents per page.
        modified_after: Only fetch documents modified after this datetime.

    Returns:
        List of document dicts from Paperless API.
    """
    all_docs: list[dict] = []
    params: dict[str, Any] = {
        "page_size": page_size,
        "ordering": "-modified",
    }
    if modified_after:
        params["modified__date__gte"] = modified_after.strftime("%Y-%m-%d")

    url = f"{_get_paperless_url()}/api/documents/"

    with httpx.Client(timeout=PAPERLESS_TIMEOUT) as client:
        while url:
            resp = client.get(url, params=params, headers=_get_paperless_headers())
            resp.raise_for_status()
            data = resp.json()
            all_docs.extend(data.get("results", []))
            url = data.get("next")
            params = {}  # next URL already contains params

    logger.info("Fetched %d documents from Paperless", len(all_docs))
    return all_docs


def sync_document(paperless_doc: dict[str, Any]) -> tuple[DocumentMetadata, bool]:
    """Upsert a single Paperless document into DocumentMetadata.

    Args:
        paperless_doc: Document dict from Paperless API.

    Returns:
        Tuple of (DocumentMetadata instance, created: bool).
    """
    doc_id = paperless_doc["id"]
    tag_names = paperless_doc.get("tag_names") or []
    correspondent = paperless_doc.get("correspondent__name") or paperless_doc.get("correspondent_name", "")

    # Parse document date
    doc_date = None
    if paperless_doc.get("created"):
        try:
            doc_date = datetime.fromisoformat(
                paperless_doc["created"].replace("Z", "+00:00")
            ).date()
        except (ValueError, TypeError):
            pass

    paperless_url = f"{_get_paperless_url()}/documents/{doc_id}/details"

    defaults = {
        "title": paperless_doc.get("title", ""),
        "correspondent": correspondent or "",
        "tags": tag_names,
        "paperless_url": paperless_url,
        "document_date": doc_date,
        "status": DocumentMetadataStatus.INDEXED,
        "paperless_updated_at": timezone.now(),
        "last_synced_at": timezone.now(),
        "tenant_id": PLATFORM_INTERNAL_TENANT_ID,
    }

    obj, created = DocumentMetadata.objects.update_or_create(
        paperless_document_id=doc_id,
        deleted_at__isnull=True,
        defaults=defaults,
    )

    if created:
        logger.info("Created DocumentMetadata for Paperless doc %d: %s", doc_id, obj.title)
    else:
        logger.debug("Updated DocumentMetadata for Paperless doc %d: %s", doc_id, obj.title)

    return obj, created


def sync_all_documents(modified_after: datetime | None = None) -> dict[str, int]:
    """Full sync: fetch all Paperless documents and upsert into DocumentMetadata.

    Args:
        modified_after: Only sync documents modified after this datetime.

    Returns:
        Dict with counts: {"created": N, "updated": N, "total": N, "errors": N}
    """
    docs = fetch_paperless_documents(modified_after=modified_after)

    created_count = 0
    updated_count = 0
    error_count = 0

    for doc in docs:
        try:
            _, created = sync_document(doc)
            if created:
                created_count += 1
            else:
                updated_count += 1
        except Exception:
            logger.exception("Failed to sync Paperless doc %s", doc.get("id"))
            error_count += 1

    result = {
        "created": created_count,
        "updated": updated_count,
        "total": len(docs),
        "errors": error_count,
    }
    logger.info("Sync complete: %s", result)
    return result
