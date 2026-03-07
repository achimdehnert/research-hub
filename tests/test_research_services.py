"""Tests for research services layer."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from django.contrib.auth import get_user_model

from apps.research.models import ResearchProject, ResearchResult
from apps.research.services import ResearchProjectService

User = get_user_model()


@pytest.mark.django_db
def test_create_project(db):
    user = User.objects.create_user(username="svc_user", password="pass", email="svc@iil.pet")
    svc = ResearchProjectService()
    project = svc.create_project(user=user, name="Test", query="AI research")
    assert project.pk is not None
    assert project.status == "draft"
    assert project.user == user


@pytest.mark.django_db
def test_create_project_with_description(db):
    user = User.objects.create_user(username="svc_user2", password="pass", email="svc2@iil.pet")
    svc = ResearchProjectService()
    project = svc.create_project(user=user, name="P2", query="query", description="desc")
    assert project.description == "desc"


@pytest.mark.django_db
async def test_run_research_success(db):
    user = await User.objects.acreate(
        username="async_user", password="pass", email="async@iil.pet"
    )
    project = await ResearchProject.objects.acreate(
        user=user, name="Async Project", query="test query"
    )

    mock_output = MagicMock()
    mock_output.success = True
    mock_output.sources = []
    mock_output.findings = []
    mock_output.summary = "Test summary"

    svc = ResearchProjectService()
    with patch.object(svc, "_build_service") as mock_build:
        mock_research_svc = MagicMock()
        mock_research_svc.research = AsyncMock(return_value=mock_output)
        mock_build.return_value = mock_research_svc

        result = await svc.run_research(project)

    assert isinstance(result, ResearchResult)
    assert result.summary == "Test summary"
    await project.arefresh_from_db()
    assert project.status == "done"


@pytest.mark.django_db
async def test_run_research_failure(db):
    user = await User.objects.acreate(
        username="fail_user", password="pass", email="fail@iil.pet"
    )
    project = await ResearchProject.objects.acreate(
        user=user, name="Fail Project", query="test"
    )

    mock_output = MagicMock()
    mock_output.success = False
    mock_output.sources = []
    mock_output.findings = []
    mock_output.summary = ""

    svc = ResearchProjectService()
    with patch.object(svc, "_build_service") as mock_build:
        mock_research_svc = MagicMock()
        mock_research_svc.research = AsyncMock(return_value=mock_output)
        mock_build.return_value = mock_research_svc

        await svc.run_research(project)

    await project.arefresh_from_db()
    assert project.status == "error"
