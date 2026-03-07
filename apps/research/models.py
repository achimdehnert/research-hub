"""Research domain models."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Workspace(models.Model):
    """Top-level container: one Workspace holds multiple Projects."""

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspaces",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_user_workspace_name"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def project_count(self) -> int:
        return self.research_projects.filter(deleted_at__isnull=True).count()


class Project(models.Model):
    """Mid-level grouping: a Project belongs to a Workspace and holds Recherchen."""

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_projects_owned",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"], name="unique_workspace_project_name"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def research_count(self) -> int:
        return self.researches.filter(deleted_at__isnull=True).count()


class ResearchProject(models.Model):
    """A single research run (Recherche) — belongs to a Project."""

    RESEARCH_TYPE_CHOICES = [
        ("web", "Web-Recherche"),
        ("academic", "Wissenschaftlich"),
        ("combined", "Kombiniert (Web + Wissenschaft)"),
        ("fact_check", "Faktencheck"),
    ]
    DEPTH_CHOICES = [
        ("quick", "Schnell (5 Quellen)"),
        ("standard", "Standard (15 Quellen)"),
        ("deep", "Tief (30 Quellen)"),
        ("exhaustive", "Exhaustiv (50 Quellen)"),
    ]
    ACADEMIC_SOURCE_CHOICES = [
        ("arxiv", "arXiv"),
        ("semantic_scholar", "Semantic Scholar"),
        ("pubmed", "PubMed"),
        ("openalex", "OpenAlex"),
    ]
    DEPTH_TO_SOURCES = {"quick": 5, "standard": 15, "deep": 30, "exhaustive": 50}
    SUMMARY_LEVEL_CHOICES = [
        ("simple", "Einfach — verständlich für alle"),
        ("medium", "Mittel — informierter Leser"),
        ("complex", "Komplex — Fachpublikum"),
        ("scientific", "Wissenschaftlich — Experten"),
    ]
    CITATION_STYLE_CHOICES = [
        ("none", "Keine Zitate"),
        ("inline", "Im Text [Autor Jahr]"),
        ("bibliography", "Literaturliste am Ende"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_projects",
    )
    # New: project FK (nullable for backward compat with existing rows)
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="researches",
    )
    # Legacy: direct workspace FK kept for data that predates Project layer
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="research_projects",
    )
    name = models.CharField(max_length=255)
    query = models.TextField()
    description = models.TextField(blank=True)
    research_type = models.CharField(
        max_length=20, choices=RESEARCH_TYPE_CHOICES, default="combined"
    )
    depth = models.CharField(
        max_length=20, choices=DEPTH_CHOICES, default="standard"
    )
    academic_sources = models.JSONField(
        default=list,
        help_text="Akademische Quellen (arxiv, semantic_scholar, pubmed, openalex)",
    )
    language = models.CharField(max_length=10, default="de")
    summary_level = models.CharField(
        max_length=20, choices=SUMMARY_LEVEL_CHOICES, default="medium"
    )
    citation_style = models.CharField(
        max_length=20, choices=CITATION_STYLE_CHOICES, default="none"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("running", "Running"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_user_project_name"
            ),
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
