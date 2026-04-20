"""DRF serializers for research-hub API."""

from rest_framework import serializers

from apps.research.models import ResearchProject, ResearchResult, Workspace


class ResearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchResult
        fields = [
            "public_id",
            "query",
            "sources_json",
            "findings_json",
            "summary",
            "created_at",
        ]
        read_only_fields = fields


class ResearchResultExportSerializer(serializers.ModelSerializer):
    """Flat export format for consumption by other hubs."""

    project_name = serializers.CharField(source="project.name", read_only=True)
    project_id = serializers.UUIDField(source="project.public_id", read_only=True)
    summary_level = serializers.CharField(source="project.summary_level", read_only=True)
    research_type = serializers.CharField(source="project.research_type", read_only=True)
    language = serializers.CharField(source="project.language", read_only=True)
    source_count = serializers.SerializerMethodField()

    class Meta:
        model = ResearchResult
        fields = [
            "public_id",
            "project_id",
            "project_name",
            "query",
            "summary",
            "summary_level",
            "research_type",
            "language",
            "source_count",
            "sources_json",
            "created_at",
        ]
        read_only_fields = fields

    def get_source_count(self, obj) -> int:
        return len(obj.sources_json) if obj.sources_json else 0


class ResearchProjectSerializer(serializers.ModelSerializer):
    results = ResearchResultSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchProject
        fields = [
            "public_id",
            "name",
            "query",
            "description",
            "status",
            "created_at",
            "results",
        ]
        read_only_fields = ["public_id", "status", "created_at"]


class WorkspaceSerializer(serializers.ModelSerializer):
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ["public_id", "name", "description", "project_count", "created_at"]
        read_only_fields = fields

    def get_project_count(self, obj) -> int:
        return obj.projects.filter(deleted_at__isnull=True).count()
