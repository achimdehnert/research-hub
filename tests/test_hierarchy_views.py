"""Tests for Workspace → Project → Recherche hierarchy views and breadcrumb context.

Also contains regression tests for known bugs:
- BUG-001: ResearchProject not linked to Project after form submit
- BUG-002: ResearchProject.workspace NULL when created via Project
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.research.models import Project, ResearchProject, Workspace

User = get_user_model()


# ── Fixtures ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="hier_user", password="pass", email="hier@iil.pet"
    )


@pytest.fixture
def workspace(user):
    return Workspace.objects.create(user=user, name="Test Workspace")


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace, user=user, name="Test Project"
    )


@pytest.fixture
def research(project, user):
    return ResearchProject.objects.create(
        user=user,
        project=project,
        workspace=project.workspace,
        name="Test Recherche",
        query="Klimawandel",
        summary_level="medium",
        citation_style="none",
        language="de",
    )


# ── Workspace views ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_should_show_workspace_list(user, workspace, client):
    client.force_login(user)
    response = client.get(reverse("research:workspace-list"))
    assert response.status_code == 200
    assert workspace.name.encode() in response.content


@pytest.mark.django_db
def test_should_show_workspace_detail_with_projects(user, workspace, project, client):
    client.force_login(user)
    response = client.get(
        reverse("research:workspace-detail", kwargs={"public_id": workspace.public_id})
    )
    assert response.status_code == 200
    assert project.name.encode() in response.content


@pytest.mark.django_db
def test_should_include_breadcrumb_in_workspace_detail(user, workspace, client):
    client.force_login(user)
    response = client.get(
        reverse("research:workspace-detail", kwargs={"public_id": workspace.public_id})
    )
    assert response.status_code == 200
    ctx = response.context
    assert "breadcrumb" in ctx
    labels = [b["label"] for b in ctx["breadcrumb"]]
    assert "Workspaces" in labels
    assert workspace.name in labels


@pytest.mark.django_db
def test_should_deny_workspace_detail_for_other_user(workspace, client, db):
    other = User.objects.create_user(
        username="other", password="pass", email="other@iil.pet"
    )
    client.force_login(other)
    response = client.get(
        reverse("research:workspace-detail", kwargs={"public_id": workspace.public_id})
    )
    assert response.status_code == 404


# ── Project views ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_should_show_project_detail(user, project, client):
    client.force_login(user)
    response = client.get(
        reverse("research:project-detail", kwargs={"project_id": project.public_id})
    )
    assert response.status_code == 200
    assert project.name.encode() in response.content


@pytest.mark.django_db
def test_should_include_breadcrumb_in_project_detail(user, workspace, project, client):
    client.force_login(user)
    response = client.get(
        reverse("research:project-detail", kwargs={"project_id": project.public_id})
    )
    ctx = response.context
    assert "breadcrumb" in ctx
    labels = [b["label"] for b in ctx["breadcrumb"]]
    assert "Workspaces" in labels
    assert workspace.name in labels
    assert project.name in labels


@pytest.mark.django_db
def test_should_create_project_under_workspace(user, workspace, client):
    client.force_login(user)
    response = client.post(
        reverse("research:project-create", kwargs={"workspace_id": workspace.public_id}),
        data={"name": "Neues Projekt", "description": "Test"},
    )
    assert response.status_code == 302
    assert Project.objects.filter(workspace=workspace, name="Neues Projekt").exists()


@pytest.mark.django_db
def test_should_deny_project_detail_for_other_user(project, client, db):
    other = User.objects.create_user(
        username="other2", password="pass", email="other2@iil.pet"
    )
    client.force_login(other)
    response = client.get(
        reverse("research:project-detail", kwargs={"project_id": project.public_id})
    )
    assert response.status_code == 404


# ── ResearchProject views ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_should_show_research_detail(user, research, client):
    client.force_login(user)
    response = client.get(
        reverse("research:research-detail", kwargs={"public_id": research.public_id})
    )
    assert response.status_code == 200
    assert research.name.encode() in response.content


@pytest.mark.django_db
def test_should_include_breadcrumb_in_research_detail(user, workspace, project, research, client):
    client.force_login(user)
    response = client.get(
        reverse("research:research-detail", kwargs={"public_id": research.public_id})
    )
    ctx = response.context
    assert "breadcrumb" in ctx
    labels = [b["label"] for b in ctx["breadcrumb"]]
    assert "Workspaces" in labels
    assert workspace.name in labels
    assert project.name in labels
    assert research.name in labels


@pytest.mark.django_db
def test_should_show_research_create_form_with_project_context(user, project, client):
    client.force_login(user)
    response = client.get(
        reverse("research:research-create") + f"?project={project.public_id}"
    )
    assert response.status_code == 200
    ctx = response.context
    assert "project" in ctx
    assert ctx["project"].pk == project.pk
    assert "workspace" in ctx
    assert ctx["workspace"].pk == project.workspace.pk


@pytest.mark.django_db
def test_should_include_breadcrumb_in_research_create(user, workspace, project, client):
    client.force_login(user)
    response = client.get(
        reverse("research:research-create") + f"?project={project.public_id}"
    )
    ctx = response.context
    assert "breadcrumb" in ctx
    labels = [b["label"] for b in ctx["breadcrumb"]]
    assert "Neue Recherche" in labels


# ── BUG-001: Research not linked to Project after POST ─────────────────────────

@pytest.mark.django_db
def test_should_link_research_to_project_after_create(user, project, client):
    """BUG-001: ResearchProjectCreateView must persist project FK on form submit.

    The view reads `project_id` from POST body, but the form template sends
    the project public_id as a hidden field named `project_id`. This test
    verifies the FK is correctly set after a valid POST.
    """
    client.force_login(user)
    response = client.post(
        reverse("research:research-create"),
        data={
            "name": "Bug-Test Recherche",
            "query": "Test query",
            "summary_level": "medium",
            "citation_style": "none",
            "language": "de",
            "research_type": "combined",
            "depth": "standard",
            "project_id": str(project.public_id),
        },
    )
    # Should redirect after success
    assert response.status_code == 302
    created = ResearchProject.objects.filter(name="Bug-Test Recherche").first()
    assert created is not None, "ResearchProject was not created"
    # BUG-001: project FK must be set
    assert created.project is not None, "BUG-001: project FK is NULL after create"
    assert created.project.pk == project.pk


# ── BUG-002: ResearchProject.workspace NULL when created via Project ──────────

@pytest.mark.django_db
def test_should_set_workspace_on_research_when_created_via_project(user, project, client):
    """BUG-002: ResearchProject.workspace must be set from project.workspace on create.

    When a Recherche is created under a Project, both `project` and `workspace`
    FKs must be populated. A NULL workspace breaks breadcrumb rendering.
    """
    client.force_login(user)
    client.post(
        reverse("research:research-create"),
        data={
            "name": "Bug-002 Recherche",
            "query": "workspace test",
            "summary_level": "medium",
            "citation_style": "none",
            "language": "de",
            "research_type": "combined",
            "depth": "standard",
            "project_id": str(project.public_id),
        },
    )
    created = ResearchProject.objects.filter(name="Bug-002 Recherche").first()
    assert created is not None
    # BUG-002: workspace must not be NULL
    assert created.workspace is not None, "BUG-002: workspace FK is NULL after create"
    assert created.workspace.pk == project.workspace.pk
