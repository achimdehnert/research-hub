from django.contrib import admin

from apps.research.models import Project, ResearchProject, ResearchResult, Workspace


class _AllObjectsAdminMixin:
    """Show soft-deleted rows in the admin (audit/restore).

    The default manager now hides ``deleted_at``-set rows; the admin must
    still reach them, so it queries the unfiltered ``all_objects`` manager.
    """

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()


@admin.register(Workspace)
class WorkspaceAdmin(_AllObjectsAdminMixin, admin.ModelAdmin):
    list_display = ["name", "user", "tenant_id", "project_count", "created_at"]
    search_fields = ["name", "user__email"]
    list_filter = ["tenant_id"]
    readonly_fields = ["public_id", "tenant_id"]


@admin.register(Project)
class ProjectAdmin(_AllObjectsAdminMixin, admin.ModelAdmin):
    list_display = ["name", "workspace", "user", "created_at"]
    search_fields = ["name", "workspace__name", "user__email"]
    list_filter = ["workspace"]
    readonly_fields = ["public_id"]


@admin.register(ResearchProject)
class ResearchProjectAdmin(_AllObjectsAdminMixin, admin.ModelAdmin):
    list_display = ["name", "project", "workspace", "status", "user", "created_at"]
    search_fields = ["name", "query", "user__email"]
    list_filter = ["status", "research_type", "depth"]
    readonly_fields = ["public_id"]


@admin.register(ResearchResult)
class ResearchResultAdmin(_AllObjectsAdminMixin, admin.ModelAdmin):
    list_display = ["project", "created_at"]
    search_fields = ["project__name", "query"]
