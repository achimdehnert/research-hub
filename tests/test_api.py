"""Tests for the REST API — auth, tenant scoping, project_count annotation."""

import pytest
from django.contrib.auth import get_user_model

from apps.research.models import Project, ResearchProject, Workspace

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="api_user", password="pass", email="api@iil.pet")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="api_other", password="pass", email="ao@iil.pet")


@pytest.fixture
def workspace(user):
    ws = Workspace.objects.create(user=user, name="API WS")
    Project.objects.create(user=user, workspace=ws, name="P1")
    Project.objects.create(user=user, workspace=ws, name="P2")
    deleted = Project.objects.create(user=user, workspace=ws, name="P3")
    deleted.deleted_at = ws.created_at
    deleted.save(update_fields=["deleted_at"])
    return ws


@pytest.mark.a2
@pytest.mark.django_db
def test_should_require_auth_for_api(client):
    response = client.get("/api/v1/workspaces/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_should_return_project_count_excluding_deleted(user, workspace, client):
    client.force_login(user)
    response = client.get("/api/v1/workspaces/")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["project_count"] == 2


@pytest.mark.django_db
def test_should_scope_workspaces_to_user(other_user, workspace, client):
    client.force_login(other_user)
    response = client.get("/api/v1/workspaces/")
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_should_return_workspace_detail_with_count(user, workspace, client):
    client.force_login(user)
    response = client.get(f"/api/v1/workspaces/{workspace.public_id}/")
    assert response.status_code == 200
    assert response.json()["project_count"] == 2


@pytest.mark.django_db
def test_should_list_research_projects_for_user_only(user, other_user, workspace, client):
    ResearchProject.objects.create(user=user, workspace=workspace, name="Mine", query="q")
    other_ws = Workspace.objects.create(user=other_user, name="Other WS")
    ResearchProject.objects.create(user=other_user, workspace=other_ws, name="Theirs", query="q")

    client.force_login(user)
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    names = [r["name"] for r in response.json()["results"]]
    assert names == ["Mine"]
