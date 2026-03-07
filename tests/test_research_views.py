"""Tests for research views — reformat HTMX endpoint."""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.research.models import ResearchProject, ResearchResult

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="view_user", password="pass", email="view@iil.pet"
    )


@pytest.fixture
def project(user):
    return ResearchProject.objects.create(
        user=user,
        name="View Test Project",
        query="test query",
        summary_level="medium",
        citation_style="none",
        language="de",
    )


@pytest.fixture
def result_with_summary(project):
    return ResearchResult.objects.create(
        project=project,
        query="test query",
        summary="**Kernaussage**\nDer Klimawandel schreitet voran.\n\n**Erkenntnisse**\n- Punkt 1\n- Punkt 2",
    )


@pytest.mark.django_db
def test_reformat_htmx_requires_post(user, project, client):
    client.force_login(user)
    response = client.get(f"/research/{project.public_id}/reformat/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_reformat_htmx_requires_htmx_header(user, project, client):
    client.force_login(user)
    response = client.post(
        f"/research/{project.public_id}/reformat/",
        data={"target_format": "bullets"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_reformat_htmx_no_summary(user, project, client):
    client.force_login(user)
    response = client.post(
        f"/research/{project.public_id}/reformat/",
        data={"target_format": "bullets"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert "Keine Zusammenfassung" in response.content.decode()


@pytest.mark.django_db
def test_reformat_htmx_fallback_no_llm(user, project, result_with_summary, client):
    """With no API key, TextReformatter falls back to rule-based transform."""
    client.force_login(user)
    with patch.dict("os.environ", {"TOGETHER_API_KEY": ""}):
        response = client.post(
            f"/research/{project.public_id}/reformat/",
            data={"target_format": "bullets"},
            HTTP_HX_REQUEST="true",
        )
    assert response.status_code == 200
    content = response.content.decode()
    assert len(content) > 0


@pytest.mark.django_db
def test_reformat_htmx_with_mock_llm(user, project, result_with_summary, client):
    """With mocked LLM, reformatted text is returned."""
    mock_result = MagicMock()
    mock_result.content = "- Punkt A\n- Punkt B\n- Punkt C"

    client.force_login(user)
    with patch("apps.research.views._make_sync_llm") as mock_factory:
        mock_factory.return_value = lambda p: "- Punkt A\n- Punkt B"
        response = client.post(
            f"/research/{project.public_id}/reformat/",
            data={"target_format": "bullets"},
            HTTP_HX_REQUEST="true",
        )
    assert response.status_code == 200
    assert len(response.content) > 0
