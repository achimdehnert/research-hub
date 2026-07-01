"""Tests for research services layer."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.research.models import ResearchProject, ResearchResult
from apps.research.services import (
    ResearchProjectService,
    _bump_content_version,
    _tenant_int,
)

User = get_user_model()


@pytest.mark.f1
def test_should_map_tenant_uuid_to_stable_signed_bigint():
    u = uuid.UUID("12345678-1234-5678-1234-567812345678")
    val = _tenant_int(u)
    assert val == _tenant_int(u)  # deterministic
    assert 0 <= val <= 0x7FFF_FFFF_FFFF_FFFF  # fits signed BigIntegerField


@pytest.mark.f1
def test_should_start_content_version_at_1_for_new_row():
    assert _bump_content_version(None, None, "abc") == 1


@pytest.mark.f1
def test_should_keep_content_version_when_sha_unchanged():
    # Republish with identical content → no version churn (ADR-130).
    assert _bump_content_version(3, "sha-same", "sha-same") == 3


@pytest.mark.f1
def test_should_increment_content_version_when_content_changed():
    # Regression guard for hardcoded version=1 (reset every republish to 1).
    assert _bump_content_version(3, "sha-old", "sha-new") == 4


def test_should_not_collide_on_uuids_sharing_first_32_bits():
    # Both share the first 8 hex digits — the old int(hex[:8]) truncation
    # collided here; the blake2b mapping must not.
    a = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    b = uuid.UUID("aaaaaaaa-ffff-ffff-ffff-ffffffffffff")
    assert _tenant_int(a) != _tenant_int(b)


@pytest.mark.django_db
def test_should_create_project(db):
    user = User.objects.create_user(username="svc_user", password="pass", email="svc@iil.pet")
    svc = ResearchProjectService()
    project = svc.create_project(user=user, name="Test", query="AI research")
    assert project.pk is not None
    assert project.status == "draft"
    assert project.user == user


@pytest.mark.django_db
def test_should_create_project_with_description(db):
    user = User.objects.create_user(username="svc_user2", password="pass", email="svc2@iil.pet")
    svc = ResearchProjectService()
    project = svc.create_project(user=user, name="P2", query="query", description="desc")
    assert project.description == "desc"


@pytest.mark.django_db(transaction=True)
def test_should_complete_research_on_success():
    user = User.objects.create_user(username="async_user", password="pass", email="async@iil.pet")
    project = ResearchProject.objects.create(user=user, name="Async Project", query="test query")
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
        result = asyncio.run(svc.run_research(project))

    assert isinstance(result, ResearchResult)
    assert result.summary == "Test summary"
    project.refresh_from_db()
    assert project.status == "done"


@pytest.mark.django_db(transaction=True)
def test_should_not_duplicate_result_on_retried_run():
    """Same run_token (Celery retry) must reuse one ResearchResult, not duplicate."""
    user = User.objects.create_user(username="idem_user", password="pass", email="idem@iil.pet")
    project = ResearchProject.objects.create(user=user, name="Idem", query="q")
    mock_output = MagicMock()
    mock_output.success = True
    mock_output.sources = []
    mock_output.findings = []
    mock_output.summary = "S"

    svc = ResearchProjectService()
    with patch.object(svc, "_build_service") as mock_build:
        mock_research_svc = MagicMock()
        mock_research_svc.research = AsyncMock(return_value=mock_output)
        mock_build.return_value = mock_research_svc
        asyncio.run(svc.run_research(project, run_token="task-abc"))
        asyncio.run(svc.run_research(project, run_token="task-abc"))

    assert ResearchResult.objects.filter(project=project).count() == 1


@pytest.mark.django_db(transaction=True)
def test_should_set_error_status_on_failure():
    user = User.objects.create_user(username="fail_user", password="pass", email="fail@iil.pet")
    project = ResearchProject.objects.create(user=user, name="Fail Project", query="test")

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
        asyncio.run(svc.run_research(project))

    project.refresh_from_db()
    assert project.status == "error"
