"""KnowledgeDocument model — Outline Wiki sync target (ADR-145, Review-Fix B3).

Platform Standards:
- BigAutoField PK (DEFAULT_AUTO_FIELD)
- public_id UUIDField (unique, non-PK)
- tenant_id for multi-tenant isolation
- deleted_at for soft-delete
- UniqueConstraint on outline_id
"""

from __future__ import annotations

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class KnowledgeCategory(models.TextChoices):
    RUNBOOK = "runbook", "Runbook"
    CONCEPT = "concept", "Architektur-Konzept"
    LESSON = "lesson", "Lesson Learned"
    ADR_DRAFT = "adr_draft", "ADR-Draft"
    HUB_DOC = "hub_doc", "Hub-Dokumentation"
    ADR_MIRROR = "adr_mirror", "ADR (Read-Only Mirror)"


class EnrichmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ENRICHED = "enriched", "Enriched"
    FAILED = "failed", "Failed"
    STALE = "stale", "Stale (>24h)"


class KnowledgeDocument(models.Model):
    """Synced Outline document with AI-enrichment metadata.

    Created/updated via HMAC-authenticated webhook from Outline.
    Enrichment (summary, keywords) via Celery + aifw.
    """

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tenant_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Tenant isolation. NULL = platform-global knowledge.",
    )

    # Outline reference
    outline_id = models.UUIDField(
        unique=True,
        db_index=True,
        help_text="Outline document UUID (from webhook payload).",
    )
    outline_url = models.URLField(max_length=500, blank=True)
    collection_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Outline collection UUID.",
    )

    # Content
    title = models.CharField(max_length=500)
    text = models.TextField(help_text="Full Markdown content from Outline.")
    category = models.CharField(
        max_length=20,
        choices=KnowledgeCategory.choices,
        default=KnowledgeCategory.RUNBOOK,
        db_index=True,
    )

    # Relations
    related_adr_numbers = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="Referenced ADR numbers, e.g. [142, 143, 145].",
    )
    related_hubs = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Hub names, e.g. ['research-hub', 'risk-hub'].",
    )

    # Content hash for change detection (Phase 12)
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 of title+text for change detection.",
    )

    # AI Enrichment (Phase 10)
    summary = models.TextField(blank=True, help_text="AI-generated summary.")
    keywords = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="AI-extracted keywords.",
    )
    enrichment_status = models.CharField(
        max_length=20,
        choices=EnrichmentStatus.choices,
        default=EnrichmentStatus.PENDING,
    )
    enriched_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    outline_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last update timestamp from Outline.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["outline_id"],
                name="unique_knowledge_outline_id",
            ),
        ]
        indexes = [
            models.Index(fields=["category"], name="idx_knowledge_category"),
            models.Index(fields=["tenant_id"], name="idx_knowledge_tenant"),
            models.Index(fields=["enrichment_status"], name="idx_knowledge_enrichment"),
        ]

    def __str__(self) -> str:
        return f"[{self.get_category_display()}] {self.title}"
