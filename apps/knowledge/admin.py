"""Admin registration for KnowledgeDocument."""

from django.contrib import admin

from apps.knowledge.models import KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "title", "category", "enrichment_status", "outline_updated_at", "updated_at",
    ]
    list_filter = ["category", "enrichment_status"]
    search_fields = ["title", "text"]
    readonly_fields = [
        "public_id", "outline_id", "outline_url", "collection_id",
        "created_at", "updated_at", "enriched_at",
    ]
