"""Document Metadata models — Paperless-ngx integration (ADR-144).

Paperless-ngx = Single Source of Truth for files + OCR text.
research-hub = Metadata, AI enrichments, platform links.

Sync: Paperless → research-hub via Celery task or management command.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class DocumentMetadataStatus(models.TextChoices):
    PENDING = "pending", _("Pending OCR")
    INDEXED = "indexed", _("Indexed")
    ENRICHED = "enriched", _("AI-Enriched")
    ERROR = "error", _("Error")


class DocumentMetadataType(models.TextChoices):
    INVOICE = "invoice", _("Invoice")
    CONTRACT = "contract", _("Contract")
    RECEIPT = "receipt", _("Receipt")
    LICENSE = "license", _("License / Certificate")
    CORRESPONDENCE = "correspondence", _("Correspondence")
    OTHER = "other", _("Other")


PLATFORM_INTERNAL_TENANT_ID = 1


class DocumentMetadata(models.Model):
    """Platform metadata for a Paperless-ngx document (ADR-144).

    Links a Paperless document ID to platform-level metadata,
    AI enrichments, and tenant isolation.
    """

    # Platform standards
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("Public ID"),
    )
    tenant_id = models.BigIntegerField(
        default=PLATFORM_INTERNAL_TENANT_ID,
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("PLATFORM_INTERNAL_TENANT_ID (1) for internal doc-hub"),
    )

    # Paperless reference
    paperless_document_id = models.IntegerField(
        db_index=True,
        verbose_name=_("Paperless Document ID"),
    )
    title = models.CharField(max_length=500, verbose_name=_("Title"))
    correspondent = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Correspondent"),
    )
    paperless_url = models.URLField(blank=True, verbose_name=_("Paperless URL"))
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Tags"),
    )

    # Classification
    status = models.CharField(
        max_length=20,
        choices=DocumentMetadataStatus.choices,
        default=DocumentMetadataStatus.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    doc_type = models.CharField(
        max_length=30,
        choices=DocumentMetadataType.choices,
        default=DocumentMetadataType.OTHER,
        db_index=True,
        verbose_name=_("Document Type"),
    )

    # Document date (from Paperless, not created_at)
    document_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Document Date"),
    )

    # AI enrichment
    ai_summary = models.TextField(blank=True, verbose_name=_("AI Summary"))
    ai_keywords = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("AI Keywords"),
    )
    ai_enriched_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("AI Enriched At"),
    )

    # Sync state
    paperless_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Paperless Update"),
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Synced At"),
    )

    # Soft-delete + timestamps (platform standard)
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Deleted At"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Document Metadata")
        verbose_name_plural = _("Document Metadata")
        ordering = ["-document_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["paperless_document_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_document_metadata_paperless_id_active",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.get_doc_type_display()}] {self.title} ({self.correspondent})"
