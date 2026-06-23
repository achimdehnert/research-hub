"""Tests for soft-delete views — workspace, project, research."""

import pytest
from django.contrib.auth import get_user_model

from apps.research.models import Project, ResearchProject, ResearchResult, Workspace

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="del_user", password="pass", email="del@iil.pet")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="del_other", password="pass", email="other@iil.pet")


@pytest.fixture
def workspace(user):
    return Workspace.objects.create(user=user, name="Del WS")


@pytest.fixture
def project(user, workspace):
    return Project.objects.create(user=user, workspace=workspace, name="Del Project")


@pytest.fixture
def research(user, workspace, project):
    return ResearchProject.objects.create(
        user=user,
        workspace=workspace,
        project=project,
        name="Del Research",
        query="q",
    )


@pytest.mark.django_db
def test_should_soft_delete_workspace_with_children(user, workspace, project, research, client):
    client.force_login(user)
    response = client.post(f"/research/workspaces/{workspace.public_id}/delete/")
    assert response.status_code == 302

    workspace.refresh_from_db()
    project.refresh_from_db()
    research.refresh_from_db()
    assert workspace.deleted_at is not None
    assert project.deleted_at is not None
    assert research.deleted_at is not None


@pytest.mark.django_db
def test_should_soft_delete_project_with_researches(user, workspace, project, research, client):
    client.force_login(user)
    response = client.post(f"/research/projects/{project.public_id}/delete/")
    assert response.status_code == 302

    workspace.refresh_from_db()
    project.refresh_from_db()
    research.refresh_from_db()
    assert workspace.deleted_at is None
    assert project.deleted_at is not None
    assert research.deleted_at is not None


@pytest.mark.django_db
def test_should_soft_delete_single_research(user, project, research, client):
    client.force_login(user)
    response = client.post(f"/research/research/{research.public_id}/delete/")
    assert response.status_code == 302

    project.refresh_from_db()
    research.refresh_from_db()
    assert project.deleted_at is None
    assert research.deleted_at is not None


@pytest.mark.django_db
def test_should_reject_delete_for_foreign_user(other_user, workspace, client):
    client.force_login(other_user)
    response = client.post(f"/research/workspaces/{workspace.public_id}/delete/")
    assert response.status_code == 404

    workspace.refresh_from_db()
    assert workspace.deleted_at is None


@pytest.mark.django_db
def test_should_reject_get_on_delete_endpoint(user, workspace, client):
    client.force_login(user)
    response = client.get(f"/research/workspaces/{workspace.public_id}/delete/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_should_hide_deleted_workspace_from_list(user, workspace, client):
    client.force_login(user)
    client.post(f"/research/workspaces/{workspace.public_id}/delete/")
    response = client.get("/research/")
    # context check — the page HTML still contains the name in the success message
    assert workspace not in response.context["workspaces"]


@pytest.mark.django_db
def test_should_cascade_soft_delete_to_research_results(user, project, research, client):
    """Deleting a research must also soft-delete its results (regression)."""
    result = ResearchResult.objects.create(project=research, query="q", summary="s")
    client.force_login(user)
    client.post(f"/research/research/{research.public_id}/delete/")
    result.refresh_from_db()
    assert result.deleted_at is not None


@pytest.mark.django_db
def test_should_hide_deleted_result_from_api(user, project, research, client):
    """A soft-deleted result must not stay readable via the API (data-leak regression)."""
    result = ResearchResult.objects.create(project=research, query="q", summary="secret")
    client.force_login(user)
    # before deletion it is reachable
    assert client.get(f"/api/v1/results/{result.public_id}/").status_code == 200
    client.post(f"/research/research/{research.public_id}/delete/")
    # after deletion the cascade hides it from the API
    assert client.get(f"/api/v1/results/{result.public_id}/").status_code == 404
