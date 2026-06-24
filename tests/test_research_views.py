"""Tests for research views — reformat HTMX endpoint (async via Celery + cache)."""

import re
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.research.models import ResearchProject, ResearchResult, Workspace

User = get_user_model()


def _extract_key(html: str) -> str:
    match = re.search(r"key=(reformat%3A[^\"&]+|reformat:[^\"&]+)", html)
    assert match, f"no reformat key in response: {html}"
    return match.group(1).replace("%3A", ":")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="view_user", password="pass", email="view@iil.pet")


@pytest.fixture
def workspace(user):
    return Workspace.objects.create(user=user, name="Test WS")


@pytest.fixture
def research(user, workspace):
    return ResearchProject.objects.create(
        user=user,
        workspace=workspace,
        name="View Test Project",
        query="test query",
        summary_level="medium",
        citation_style="none",
        language="de",
    )


@pytest.fixture
def result_with_summary(research):
    return ResearchResult.objects.create(
        project=research,
        query="test query",
        summary="**Kernaussage**\nDer Klimawandel schreitet voran.\n\n**Erkenntnisse**\n- Punkt 1\n- Punkt 2",
    )


@pytest.mark.django_db
def test_should_reject_reformat_get_request(user, research, client):
    client.force_login(user)
    response = client.get(f"/research/research/{research.public_id}/reformat/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_should_reject_reformat_without_htmx_header(user, research, client):
    client.force_login(user)
    response = client.post(
        f"/research/research/{research.public_id}/reformat/",
        data={"target_format": "bullets"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_should_show_notice_when_no_summary(user, research, client):
    client.force_login(user)
    response = client.post(
        f"/research/research/{research.public_id}/reformat/",
        data={"target_format": "bullets"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert "Keine Zusammenfassung" in response.content.decode()


@pytest.mark.a6
@pytest.mark.django_db
def test_should_reject_invalid_target_format(user, research, result_with_summary, client):
    client.force_login(user)
    response = client.post(
        f"/research/research/{research.public_id}/reformat/",
        data={"target_format": "evil"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 400


@pytest.mark.u3
@pytest.mark.django_db
def test_should_return_polling_partial_on_post(user, research, result_with_summary, client):
    """POST dispatches the Celery task and returns the polling partial."""
    client.force_login(user)
    with patch("apps.research.tasks._make_sync_aifw_llm") as mock_factory:
        mock_factory.return_value = lambda p: "- Punkt A\n- Punkt B"
        response = client.post(
            f"/research/research/{research.public_id}/reformat/",
            data={"target_format": "bullets"},
            HTTP_HX_REQUEST="true",
        )
    assert response.status_code == 200
    html = response.content.decode()
    assert "Formatierung läuft" in html
    assert "reformat/status/" in html


@pytest.mark.django_db
def test_should_return_result_after_task_completes(user, research, result_with_summary, client):
    """Eager Celery runs the task inline — the status poll returns the summary."""
    client.force_login(user)
    with patch("apps.research.tasks._make_sync_aifw_llm") as mock_factory:
        mock_factory.return_value = lambda p: "- Punkt A\n- Punkt B"
        response = client.post(
            f"/research/research/{research.public_id}/reformat/",
            data={"target_format": "bullets"},
            HTTP_HX_REQUEST="true",
        )
    key = _extract_key(response.content.decode())
    status = client.get(
        f"/research/research/{research.public_id}/reformat/status/",
        {"key": key},
        HTTP_HX_REQUEST="true",
    )
    assert status.status_code == 200
    body = status.content.decode()
    assert "Formatierung läuft" not in body
    assert len(body.strip()) > 0


@pytest.mark.django_db
def test_should_reject_foreign_cache_key(user, research, result_with_summary, client):
    """Cache keys not belonging to this research's result are rejected."""
    client.force_login(user)
    response = client.get(
        f"/research/research/{research.public_id}/reformat/status/",
        {"key": "reformat:999999:bullets:abc"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 400
