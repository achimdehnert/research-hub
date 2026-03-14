"""Admin registration for KnowledgeDocument (ADR-145 Phase 12)."""

from django.contrib import admin

from apps.knowledge.models import EnrichmentStatus, KnowledgeDocument


def retry_enrichment(modeladmin, request, queryset):
    """Re-queue selected documents for AI enrichment."""
    from apps.knowledge.tasks import enrich_knowledge_document_task

    count = 0
    for doc in queryset:
        doc.enrichment_status = EnrichmentStatus.PENDING
        doc.save(update_fields=["enrichment_status", "updated_at"])
        enrich_knowledge_document_task.delay(doc.pk)
        count += 1
    modeladmin.message_user(
        request, f"{count} document(s) queued for enrichment.",
    )


retry_enrichment.short_description = "Retry AI enrichment"


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "enrichment_status",
        "keyword_count",
        "outline_updated_at",
        "updated_at",
    ]
    list_filter = ["category", "enrichment_status"]
    search_fields = ["title", "text", "summary"]
    readonly_fields = [
        "public_id",
        "outline_id",
        "outline_url",
        "collection_id",
        "content_hash",
        "created_at",
        "updated_at",
        "enriched_at",
    ]
    actions = [retry_enrichment]

    @admin.display(description="Keywords")
    def keyword_count(self, obj):
        return len(obj.keywords) if obj.keywords else 0
