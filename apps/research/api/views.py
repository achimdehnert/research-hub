"""DRF API views for research-hub."""
from rest_framework import generics, permissions

from apps.research.api.serializers import ResearchProjectSerializer
from apps.research.models import ResearchProject
from apps.research.tasks import run_research_task


class ResearchProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ResearchProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ResearchProject.objects.filter(
            user=self.request.user, deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        project = serializer.save(user=self.request.user)
        run_research_task.delay(project.pk)


class ResearchProjectDetailView(generics.RetrieveAPIView):
    serializer_class = ResearchProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"

    def get_queryset(self):
        return ResearchProject.objects.filter(
            user=self.request.user, deleted_at__isnull=True
        )
