from django.contrib import admin

from apps.research.models import Project, ResearchProject, ResearchResult, Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "created_at"]
    search_fields = ["name", "user__email"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "user", "created_at"]
    search_fields = ["name", "workspace__name", "user__email"]
    list_filter = ["workspace"]


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "workspace", "status", "user", "created_at"]
    search_fields = ["name", "query", "user__email"]
    list_filter = ["status", "research_type", "depth"]


@admin.register(ResearchResult)
class ResearchResultAdmin(admin.ModelAdmin):
    list_display = ["project", "created_at"]
    search_fields = ["project__name", "query"]
