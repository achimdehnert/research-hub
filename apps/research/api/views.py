"""DRF API views for research-hub."""

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
        return ResearchResult.objects.filter(project__user=self.request.user)


class ResearchResultExportView(generics.RetrieveAPIView):
    """Export endpoint — flat summary format for other hubs to consume."""

    serializer_class = ResearchResultExportSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return ResearchResult.objects.filter(project__user=self.request.user).select_related(
            "project"
        )


class WorkspaceListView(generics.ListAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(user=self.request.user, deleted_at__isnull=True)


class WorkspaceDetailView(generics.RetrieveAPIView):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return Workspace.objects.filter(user=self.request.user, deleted_at__isnull=True)
