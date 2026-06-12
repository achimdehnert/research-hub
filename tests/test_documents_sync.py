"""Tests for documents app — Paperless sync upsert logic (ADR-144)."""

import pytest

from apps.documents.models import DocumentMetadata, DocumentMetadataStatus
from apps.documents.services import sync_all_documents, sync_document


def _paperless_doc(doc_id=1, **overrides):
    doc = {
        "id": doc_id,
        "title": f"Rechnung {doc_id}",
        "tag_names": ["finanzen"],
        "correspondent_name": "Telekom",
        "created": "2026-01-15T10:00:00Z",
    }
    doc.update(overrides)
    return doc


@pytest.mark.django_db
def test_should_create_metadata_on_first_sync():
    obj, created = sync_document(_paperless_doc())
    assert created is True
    assert obj.title == "Rechnung 1"
    assert obj.status == DocumentMetadataStatus.INDEXED
    assert obj.tags == ["finanzen"]
    assert str(obj.document_date) == "2026-01-15"


@pytest.mark.django_db
def test_should_update_existing_metadata_on_resync():
    sync_document(_paperless_doc())
    obj, created = sync_document(_paperless_doc(title="Rechnung 1 (korrigiert)"))
    assert created is False
    assert obj.title == "Rechnung 1 (korrigiert)"
    assert DocumentMetadata.objects.count() == 1


@pytest.mark.django_db
def test_should_tolerate_invalid_created_date():
    obj, _ = sync_document(_paperless_doc(doc_id=2, created="not-a-date"))
    assert obj.document_date is None


@pytest.mark.django_db
def test_should_count_errors_without_aborting_sync(monkeypatch):
    docs = [_paperless_doc(doc_id=1), {"broken": True}, _paperless_doc(doc_id=3)]
    monkeypatch.setattr(
        "apps.documents.services.fetch_paperless_documents", lambda modified_after=None: docs
    )
    result = sync_all_documents()
    assert result == {"created": 2, "updated": 0, "total": 3, "errors": 1}
