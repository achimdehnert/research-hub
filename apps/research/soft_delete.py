"""Centralised soft-delete cascades for the research hierarchy.

One place owns the cascade order so a new child model or a new deletion
path cannot forget a level (which used to leave orphaned, still-visible
rows). Each function marks only currently-alive rows and runs in a single
transaction. ``all_objects`` is used deliberately so the cascade is immune
to the default manager's alive-only filtering.

Hierarchy: Workspace → Project → ResearchProject → ResearchResult.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.research.models import Project, ResearchProject, ResearchResult, Workspace


@transaction.atomic
def soft_delete_workspace(workspace: Workspace) -> None:
    """Soft-delete a workspace and every project, research and result under it."""
    now = timezone.now()
    ResearchResult.all_objects.filter(project__workspace=workspace, deleted_at__isnull=True).update(
        deleted_at=now
    )
    ResearchProject.all_objects.filter(workspace=workspace, deleted_at__isnull=True).update(
        deleted_at=now
    )
    Project.all_objects.filter(workspace=workspace, deleted_at__isnull=True).update(deleted_at=now)
    Workspace.all_objects.filter(pk=workspace.pk, deleted_at__isnull=True).update(deleted_at=now)


@transaction.atomic
def soft_delete_project(project: Project) -> None:
    """Soft-delete a project and every research and result under it."""
    now = timezone.now()
    ResearchResult.all_objects.filter(project__project=project, deleted_at__isnull=True).update(
        deleted_at=now
    )
    ResearchProject.all_objects.filter(project=project, deleted_at__isnull=True).update(
        deleted_at=now
    )
    Project.all_objects.filter(pk=project.pk, deleted_at__isnull=True).update(deleted_at=now)


@transaction.atomic
def soft_delete_research(research: ResearchProject) -> None:
    """Soft-delete a single research and its results."""
    now = timezone.now()
    ResearchResult.all_objects.filter(project=research, deleted_at__isnull=True).update(
        deleted_at=now
    )
    ResearchProject.all_objects.filter(pk=research.pk, deleted_at__isnull=True).update(
        deleted_at=now
    )
