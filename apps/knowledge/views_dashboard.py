"""Knowledge Dashboard — staff-only overview of synced Outline documents."""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.knowledge.models import (
    EnrichmentStatus,
    KnowledgeCategory,
    KnowledgeDocument,
)


@staff_member_required
def knowledge_dashboard(request: HttpRequest) -> HttpResponse:
    """Main knowledge dashboard with stats and document list."""
    qs = KnowledgeDocument.objects.filter(deleted_at__isnull=True)

    # Filter by category
    category_filter = request.GET.get("category", "")
    if category_filter:
        qs = qs.filter(category=category_filter)

    # Filter by enrichment status
    status_filter = request.GET.get("status", "")
    if status_filter:
        qs = qs.filter(enrichment_status=status_filter)

    # Search
    search_query = request.GET.get("q", "")
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query)
            | Q(summary__icontains=search_query)
            | Q(keywords__contains=[search_query])
        )

    paginator = Paginator(qs.order_by("-updated_at"), 50)
    documents = paginator.get_page(request.GET.get("page"))

    # Query string without page — pagination links keep active filters
    filter_params = request.GET.copy()
    filter_params.pop("page", None)
    base_query = filter_params.urlencode()

    # Stats
    all_docs = KnowledgeDocument.objects.filter(deleted_at__isnull=True)
    stats = {
        "total": all_docs.count(),
        "enriched": all_docs.filter(
            enrichment_status=EnrichmentStatus.ENRICHED,
        ).count(),
        "pending": all_docs.filter(
            enrichment_status=EnrichmentStatus.PENDING,
        ).count(),
        "failed": all_docs.filter(
            enrichment_status=EnrichmentStatus.FAILED,
        ).count(),
    }

    # Category breakdown
    category_counts = all_docs.values("category").annotate(count=Count("id")).order_by("-count")
    categories = [
        {
            "key": c["category"],
            "label": dict(KnowledgeCategory.choices).get(
                c["category"],
                c["category"],
            ),
            "count": c["count"],
        }
        for c in category_counts
    ]

    return render(
        request,
        "knowledge/dashboard.html",
        {
            "documents": documents,
            "page_obj": documents,
            "base_query": base_query,
            "stats": stats,
            "categories": categories,
            "category_filter": category_filter,
            "status_filter": status_filter,
            "search_query": search_query,
            "category_choices": KnowledgeCategory.choices,
            "status_choices": EnrichmentStatus.choices,
            "breadcrumb": [
                {"label": "Knowledge Dashboard", "url": ""},
            ],
        },
    )
