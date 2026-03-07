"""Research domain models."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class ResearchProject(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_projects",
    )
    name = models.CharField(max_length=255)
    query = models.TextField()
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("draft", "Draft"), ("running", "Running"), ("done", "Done"), ("error", "Error")],
        default="draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_user_project_name"),
        ]

    def __str__(self) -> str:
        return self.name


class ResearchResult(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="results"
    )
    query = models.TextField()
    sources_json = models.JSONField(default=list)
    findings_json = models.JSONField(default=list)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.project.name} — {self.created_at:%Y-%m-%d}"
