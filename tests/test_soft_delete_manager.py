"""Tests for the SoftDeleteManager + centralised cascade (A1/A2)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.research.models import Project, ResearchProject, ResearchResult, Workspace
from apps.research.soft_delete import (
    soft_delete_project,
    soft_delete_research,
    soft_delete_workspace,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sd_user", password="pass", email="sd@iil.pet")


@pytest.fixture
def workspace(user):
    return Workspace.objects.create(user=user, name="SD WS")


@pytest.fixture
def project(user, workspace):
    return Project.objects.create(user=user, workspace=workspace, name="SD Project")


@pytest.fixture
def research(user, workspace, project):
    return ResearchProject.objects.create(
        user=user, workspace=workspace, project=project, name="SD Research", query="q"
    )


@pytest.fixture
def result(research):
    return ResearchResult.objects.create(project=research, query="q")


@pytest.mark.django_db
def test_should_hide_soft_deleted_from_default_manager(workspace):
    Workspace.all_objects.filter(pk=workspace.pk).update(deleted_at=timezone.now())
    assert not Workspace.objects.filter(pk=workspace.pk).exists()


@pytest.mark.django_db
def test_should_keep_soft_deleted_in_all_objects(workspace):
    Workspace.all_objects.filter(pk=workspace.pk).update(deleted_at=timezone.now())
    assert Workspace.all_objects.filter(pk=workspace.pk).exists()


@pytest.mark.django_db
def test_should_expose_alive_and_dead_queryset_helpers(user):
    live = Workspace.objects.create(user=user, name="alive")
    dead = Workspace.objects.create(user=user, name="dead")
    Workspace.all_objects.filter(pk=dead.pk).update(deleted_at=timezone.now())
    assert list(Workspace.all_objects.alive().values_list("pk", flat=True)) == [live.pk]
    assert list(Workspace.all_objects.dead().values_list("pk", flat=True)) == [dead.pk]


@pytest.mark.django_db
def test_should_resolve_forward_fk_to_soft_deleted_parent(result, research):
    """base_manager_name='all_objects' keeps result.project reachable after soft-delete."""
    ResearchProject.all_objects.filter(pk=research.pk).update(deleted_at=timezone.now())
    fresh = ResearchResult.all_objects.get(pk=result.pk)
    assert fresh.project.pk == research.pk  # would raise DoesNotExist if base manager filtered


@pytest.mark.django_db
def test_should_cascade_soft_delete_workspace_to_all_descendants(
    workspace, project, research, result
):
    soft_delete_workspace(workspace)
    for obj in (workspace, project, research, result):
        obj.refresh_from_db()
        assert obj.deleted_at is not None


@pytest.mark.django_db
def test_should_cascade_soft_delete_project_but_spare_workspace(
    workspace, project, research, result
):
    soft_delete_project(project)
    workspace.refresh_from_db()
    assert workspace.deleted_at is None
    for obj in (project, research, result):
        obj.refresh_from_db()
        assert obj.deleted_at is not None


@pytest.mark.django_db
def test_should_cascade_soft_delete_research_but_spare_project(
    workspace, project, research, result
):
    soft_delete_research(research)
    for obj in (workspace, project):
        obj.refresh_from_db()
        assert obj.deleted_at is None
    for obj in (research, result):
        obj.refresh_from_db()
        assert obj.deleted_at is not None
