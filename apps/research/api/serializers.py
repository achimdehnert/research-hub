"""DRF serializers for research-hub API."""
from rest_framework import serializers
from apps.research.models import ResearchProject, ResearchResult


class ResearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchResult
        fields = ["public_id", "query", "sources_json", "findings_json", "summary", "created_at"]
        read_only_fields = fields


class ResearchProjectSerializer(serializers.ModelSerializer):
    results = ResearchResultSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchProject
        fields = ["public_id", "name", "query", "description", "status", "created_at", "results"]
        read_only_fields = ["public_id", "status", "created_at"]
