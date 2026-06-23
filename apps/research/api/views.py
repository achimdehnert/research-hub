"""DRF API views for research-hub.

Scope: every queryset is filtered to ``request.user`` (or ``project__user``).
The ``/api/`` prefix is tenant-exempt in the middleware, so the API has no
org/tenant context — it intentionally exposes only the caller's *personal*
objects, never org-shared workspaces (those are reachable via the web UI).
Soft-deleted rows (``deleted_at`` set) are excluded everywhere.
"""

from django.db.models import Count, Q
from rest_framework import generics, permissions

from apps.research.api.serializers import (
    ResearchProjectSerializer,
    ResearchResultExportSerializer,
    ResearchResultSerializer,
    WorkspaceSerializer,
)
from apps.research.models import ResearchProject, ResearchResult, Workspace
from apps.research.tasks import run_research_task


class ResearchProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ResearchProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ResearchProject.objects.filter(user=self.request.user, deleted_at__isnull=True)

    def perform_create(self, serializer):
        project = serializer.save(user=self.request.user)
        run_research_task.delay(project.pk)


class ResearchProjectDetailView(generics.RetrieveAPIView):
    serializer_class = ResearchProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return ResearchProject.objects.filter(user=self.request.user, deleted_at__isnull=True)


class ResearchResultDetailView(generics.RetrieveAPIView):
    serializer_class = ResearchResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return ResearchResult.objects.filter(
            project__user=self.request.user,
            deleted_at__isnull=True,
            project__deleted_at__isnull=True,
        )


class ResearchResultExportView(generics.RetrieveAPIView):
    """Export endpoint — flat summary format for other hubs to consume."""

    serializer_class = ResearchResultExportSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return ResearchResult.objects.filter(
            project__user=self.request.user,
            deleted_at__isnull=True,
            project__deleted_at__isnull=True,
        ).select_related("project")


def _workspace_qs(user):
    # num_projects via annotation — one query instead of one COUNT per workspace
    return (
        Workspace.objects.filter(user=user, deleted_at__isnull=True)
        .annotate(num_projects=Count("projects", filter=Q(projects__deleted_at__isnull=True)))
        .order_by("-created_at")
    )


class WorkspaceListView(generics.ListAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _workspace_qs(self.request.user)


class WorkspaceDetailView(generics.RetrieveAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return _workspace_qs(self.request.user)
