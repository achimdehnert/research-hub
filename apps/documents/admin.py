"""Admin configuration for DocumentMetadata (ADR-144)."""
from django.contrib import admin

from .models import DocumentMetadata


@admin.register(DocumentMetadata)
class DocumentMetadataAdmin(admin.ModelAdmin):
    list_display = [
        "paperless_document_id",
        "title",
        "correspondent",
        "doc_type",
        "status",
        "document_date",
        "last_synced_at",
    ]
    list_filter = ["status", "doc_type", "tenant_id"]
    search_fields = ["title", "correspondent", "ai_summary"]
    readonly_fields = [
        "public_id",
        "paperless_document_id",
        "paperless_url",
        "paperless_updated_at",
        "last_synced_at",
        "ai_enriched_at",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "document_date"
