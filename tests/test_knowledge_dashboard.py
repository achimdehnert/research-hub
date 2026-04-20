"""Tests for Knowledge Dashboard (staff-only view)."""

from __future__ import annotations


from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.knowledge.models import (
    EnrichmentStatus,
    KnowledgeCategory,
    KnowledgeDocument,
)

User = get_user_model()


class TestKnowledgeDashboardAccess(TestCase):
    """Test dashboard access control (staff-only)."""

    def setUp(self):
        self.url = reverse("knowledge:dashboard")
        self.client = Client()

    def test_should_redirect_anonymous_to_login(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 302
        assert "/admin/login/" in resp.url or "login" in resp.url

    def test_should_deny_non_staff_user(self):
        user = User.objects.create_user(
            username="regular",
            email="regular@test.local",
            password="testpass123",
        )
        self.client.force_login(user)
        resp = self.client.get(self.url)
        assert resp.status_code == 302

    def test_should_allow_staff_user(self):
        user = User.objects.create_user(
            username="staff",
            email="staff@test.local",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(user)
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert b"Knowledge Dashboard" in resp.content


class TestKnowledgeDashboardContent(TestCase):
    """Test dashboard content rendering."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="admin",
            email="admin@test.local",
            password="testpass123",
            is_staff=True,
        )
        cls.doc_enriched = KnowledgeDocument.objects.create(
            outline_id="10000000-0000-0000-0000-000000000001",
            title="OIDC Troubleshooting Guide",
            text="# OIDC\n\nStep-by-step guide.",
            category=KnowledgeCategory.RUNBOOK,
            enrichment_status=EnrichmentStatus.ENRICHED,
            summary="Guide for OIDC debugging",
            keywords=["oidc", "authentik", "sso"],
        )
        cls.doc_pending = KnowledgeDocument.objects.create(
            outline_id="20000000-0000-0000-0000-000000000002",
            title="RLS Rollout Template",
            text="# RLS\n\nTemplate for rollout.",
            category=KnowledgeCategory.CONCEPT,
            enrichment_status=EnrichmentStatus.PENDING,
        )
        cls.doc_failed = KnowledgeDocument.objects.create(
            outline_id="30000000-0000-0000-0000-000000000003",
            title="Failed Enrichment Doc",
            text="# Failed\n\nContent.",
            category=KnowledgeCategory.LESSON,
            enrichment_status=EnrichmentStatus.FAILED,
        )
        cls.url = reverse("knowledge:dashboard")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_should_show_all_documents(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert b"OIDC Troubleshooting" in resp.content
        assert b"RLS Rollout" in resp.content
        assert b"Failed Enrichment" in resp.content

    def test_should_show_correct_stats(self):
        resp = self.client.get(self.url)
        ctx = resp.context
        assert ctx["stats"]["total"] == 3
        assert ctx["stats"]["enriched"] == 1
        assert ctx["stats"]["pending"] == 1
        assert ctx["stats"]["failed"] == 1

    def test_should_filter_by_category(self):
        resp = self.client.get(self.url + "?category=runbook")
        assert resp.status_code == 200
        assert b"OIDC Troubleshooting" in resp.content
        assert b"RLS Rollout" not in resp.content

    def test_should_filter_by_status(self):
        resp = self.client.get(self.url + "?status=failed")
        assert resp.status_code == 200
        assert b"Failed Enrichment" in resp.content
        assert b"OIDC Troubleshooting" not in resp.content

    def test_should_search_by_title(self):
        resp = self.client.get(self.url + "?q=OIDC")
        assert resp.status_code == 200
        assert b"OIDC Troubleshooting" in resp.content
        assert b"RLS Rollout" not in resp.content

    def test_should_show_keywords_for_enriched(self):
        resp = self.client.get(self.url)
        assert b"oidc" in resp.content
        assert b"authentik" in resp.content

    def test_should_show_category_counts(self):
        resp = self.client.get(self.url)
        ctx = resp.context
        categories = {c["key"]: c["count"] for c in ctx["categories"]}
        assert categories["runbook"] == 1
        assert categories["concept"] == 1
        assert categories["lesson"] == 1

    def test_should_exclude_soft_deleted(self):
        from django.utils import timezone

        self.doc_failed.deleted_at = timezone.now()
        self.doc_failed.save()

        resp = self.client.get(self.url)
        ctx = resp.context
        assert ctx["stats"]["total"] == 2
        assert b"Failed Enrichment" not in resp.content

        # Cleanup
        self.doc_failed.deleted_at = None
        self.doc_failed.save()

    def test_should_combine_filters(self):
        resp = self.client.get(
            self.url + "?category=runbook&status=enriched",
        )
        assert resp.status_code == 200
        assert b"OIDC Troubleshooting" in resp.content
        # Only 1 doc matches both filters
        docs = resp.context["documents"]
        assert len(docs) == 1
