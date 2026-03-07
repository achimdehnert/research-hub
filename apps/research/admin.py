from django.contrib import admin

from apps.research.models import ResearchProject, ResearchResult


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "query"]
    readonly_fields = ["public_id", "created_at", "updated_at"]


@admin.register(ResearchResult)
class ResearchResultAdmin(admin.ModelAdmin):
    list_display = ["project", "created_at"]
    readonly_fields = ["public_id", "created_at"]
