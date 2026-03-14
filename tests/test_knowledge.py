"""Tests for apps.knowledge — HMAC webhook, service layer, model (ADR-145)."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from django.db import IntegrityError
from django.test import RequestFactory, TestCase

from apps.knowledge.models import (
    EnrichmentStatus,
    KnowledgeCategory,
    KnowledgeDocument,
)
from apps.knowledge.services import (
    mark_enrichment_complete,
    mark_enrichment_failed,
    soft_delete_document,
    sync_document_from_outline,
)
from apps.knowledge.views import _verify_hmac, outline_webhook


class TestKnowledgeDocumentModel(TestCase):
    """Test KnowledgeDocument model basics."""

    def test_should_create_document_with_defaults(self):
        doc = KnowledgeDocument.objects.create(
            outline_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            title="Test Runbook",
            text="# Test\n\nContent here.",
        )
        assert doc.pk is not None
        assert doc.public_id is not None
        assert doc.category == KnowledgeCategory.RUNBOOK
        assert doc.enrichment_status == EnrichmentStatus.PENDING
        assert doc.deleted_at is None

    def test_should_enforce_unique_outline_id(self):
        KnowledgeDocument.objects.create(
            outline_id="11111111-2222-3333-4444-555555555555",
            title="Doc A",
            text="Content A",
        )
        with pytest.raises(IntegrityError):
            KnowledgeDocument.objects.create(
                outline_id="11111111-2222-3333-4444-555555555555",
                title="Doc B",
                text="Content B",
            )

    def test_should_display_category_in_str(self):
        doc = KnowledgeDocument(
            outline_id="aaaaaaaa-1111-2222-3333-444444444444",
            title="OIDC Guide",
            category=KnowledgeCategory.RUNBOOK,
        )
        assert "[Runbook]" in str(doc)
        assert "OIDC Guide" in str(doc)


class TestSyncService(TestCase):
    """Test sync_document_from_outline service function."""

    def _make_payload(
        self,
        doc_id="a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e4e4",
        title="Test",
        text="# Test",
    ):
        return {
            "event": "documents.create",
            "data": {
                "id": doc_id,
                "title": title,
                "text": text,
                "url": "/doc/test-abc",
                "collectionId": "a67c9777-3bc3-401a-9de3-91f0cc6c56d9",
                "updatedAt": "2026-03-14T10:00:00Z",
            },
        }

    def test_should_create_new_document(self):
        uid = "10000000-0000-0000-0000-000000000001"
        payload = self._make_payload(
            doc_id=uid,
            title="New Runbook",
        )
        doc = sync_document_from_outline(payload)
        assert doc.title == "New Runbook"
        assert doc.category == KnowledgeCategory.RUNBOOK
        assert str(doc.outline_id) == uid
        assert KnowledgeDocument.objects.count() == 1

    def test_should_update_existing_document(self):
        payload = self._make_payload(
            doc_id="20000000-0000-0000-0000-000000000002",
            title="V1",
        )
        sync_document_from_outline(payload)

        payload["data"]["title"] = "V2"
        payload["data"]["text"] = "Updated content"
        doc = sync_document_from_outline(payload)

        assert doc.title == "V2"
        assert doc.text == "Updated content"
        assert KnowledgeDocument.objects.count() == 1

    def test_should_map_collection_to_category(self):
        payload = self._make_payload(
            doc_id="30000000-0000-0000-0000-000000000003",
        )
        payload["data"]["collectionId"] = "db8291c2-f135-4834-878e-224db5673ab6"
        doc = sync_document_from_outline(payload)
        assert doc.category == KnowledgeCategory.LESSON

    def test_should_raise_on_missing_id(self):
        with pytest.raises(ValueError, match="Missing document id"):
            sync_document_from_outline({"data": {}})


class TestSoftDelete(TestCase):
    """Test soft_delete_document service function."""

    def test_should_soft_delete_existing(self):
        uid = "40000000-0000-0000-0000-000000000004"
        KnowledgeDocument.objects.create(
            outline_id=uid,
            title="To Delete",
            text="Content",
        )
        assert soft_delete_document(uid) is True
        doc = KnowledgeDocument.objects.get(outline_id=uid)
        assert doc.deleted_at is not None

    def test_should_return_false_for_missing(self):
        assert soft_delete_document(
            "50000000-0000-0000-0000-000000000005",
        ) is False


class TestEnrichment(TestCase):
    """Test enrichment service functions."""

    def test_should_mark_enrichment_complete(self):
        doc = KnowledgeDocument.objects.create(
            outline_id="60000000-0000-0000-0000-000000000006",
            title="Enrich Me",
            text="Content",
        )
        mark_enrichment_complete(doc, "Summary text", ["keyword1", "keyword2"])
        doc.refresh_from_db()
        assert doc.enrichment_status == EnrichmentStatus.ENRICHED
        assert doc.summary == "Summary text"
        assert doc.keywords == ["keyword1", "keyword2"]
        assert doc.enriched_at is not None

    def test_should_mark_enrichment_failed(self):
        doc = KnowledgeDocument.objects.create(
            outline_id="70000000-0000-0000-0000-000000000007",
            title="Fail Me",
            text="Content",
        )
        mark_enrichment_failed(doc, "LLM timeout")
        doc.refresh_from_db()
        assert doc.enrichment_status == EnrichmentStatus.FAILED


class TestHMACVerification(TestCase):
    """Test HMAC-SHA256 webhook signature verification."""

    def test_should_verify_valid_signature(self):
        secret = "test-webhook-secret-12345"
        body = b'{"event": "documents.create"}'
        sig = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        assert _verify_hmac(body, sig, secret) is True

    def test_should_reject_invalid_signature(self):
        assert _verify_hmac(b"body", "sha256=wrong", "secret") is False

    def test_should_reject_empty_secret(self):
        assert _verify_hmac(b"body", "sha256=abc", "") is False

    def test_should_reject_empty_signature(self):
        assert _verify_hmac(b"body", "", "secret") is False


class TestWebhookView(TestCase):
    """Test outline_webhook view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.secret = "test-secret-for-webhook"

    def _signed_request(self, payload: dict, secret: str | None = None):
        body = json.dumps(payload).encode()
        s = secret or self.secret
        sig = "sha256=" + hmac.new(
            s.encode(), body, hashlib.sha256
        ).hexdigest()
        request = self.factory.post(
            "/knowledge/webhook/outline/",
            data=body,
            content_type="application/json",
            HTTP_X_OUTLINE_SIGNATURE=sig,
        )
        return request

    def test_should_reject_unsigned_request(self):
        request = self.factory.post(
            "/knowledge/webhook/outline/",
            data=b'{}',
            content_type="application/json",
        )
        from unittest.mock import patch
        with patch("apps.knowledge.views.WEBHOOK_SECRET", "real-secret"):
            response = outline_webhook(request)
        assert response.status_code == 401

    def test_should_reject_wrong_signature(self):
        request = self._signed_request(
            {"event": "documents.create", "data": {"id": "123"}},
            secret="wrong-secret",
        )
        from unittest.mock import patch
        with patch("apps.knowledge.views.WEBHOOK_SECRET", self.secret):
            response = outline_webhook(request)
        assert response.status_code == 401

    def test_should_accept_valid_create_event(self):
        payload = {
            "event": "documents.create",
            "data": {"id": "doc-123", "title": "Test"},
        }
        request = self._signed_request(payload)
        from unittest.mock import patch
        with patch("apps.knowledge.views.WEBHOOK_SECRET", self.secret), \
             patch("apps.knowledge.views.sync_knowledge_document_task") as mock_task:
            response = outline_webhook(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "accepted"
        mock_task.delay.assert_called_once_with(payload)

    def test_should_ignore_unsupported_event(self):
        payload = {"event": "collections.create", "data": {"id": "col-1"}}
        request = self._signed_request(payload)
        from unittest.mock import patch
        with patch("apps.knowledge.views.WEBHOOK_SECRET", self.secret):
            response = outline_webhook(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ignored"
