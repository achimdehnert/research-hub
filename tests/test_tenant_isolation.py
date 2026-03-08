"""Tests for multi-tenant data isolation in research-hub.

Verifies that:
- User A in Tenant-1 cannot see Workspace of User B in Tenant-2
- User without tenant sees only own personal workspaces
- Tenant-assigned workspace is not visible without tenant context
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from apps.research.models import Project, ResearchProject, Workspace
from apps.research.views import _tenant_workspace_qs

User = get_user_model()

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username="user_a", password="pass", email="user_a@iil.pet"
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username="user_b", password="pass", email="user_b@iil.pet"
    )


@pytest.fixture
def ws_tenant_a(user_a):
    return Workspace.objects.create(
        user=user_a, name="Tenant-A Workspace", tenant_id=TENANT_A
    )


@pytest.fixture
def ws_tenant_b(user_b):
    return Workspace.objects.create(
        user=user_b, name="Tenant-B Workspace", tenant_id=TENANT_B
    )


@pytest.fixture
def ws_personal_a(user_a):
    return Workspace.objects.create(
        user=user_a, name="Personal Workspace A", tenant_id=None
    )


@pytest.fixture
def rf():
    return RequestFactory()


def _make_request(rf, user, tenant_id=None):
    request = rf.get("/")
    request.user = user
    request.tenant_id = tenant_id
    request.tenant = None
    return request


# ── Tenant isolation tests ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_should_not_see_other_tenants_workspace(
    rf, user_a, ws_tenant_a, ws_tenant_b
):
    """User A in Tenant A must not see Workspace from Tenant B."""
    request = _make_request(rf, user_a, tenant_id=TENANT_A)
    qs = _tenant_workspace_qs(request)
    assert ws_tenant_a in qs
    assert ws_tenant_b not in qs


@pytest.mark.django_db
def test_should_not_see_other_users_personal_workspace(
    rf, user_a, user_b, ws_personal_a
):
    """User B must not see personal Workspace of User A."""
    request = _make_request(rf, user_b, tenant_id=None)
    qs = _tenant_workspace_qs(request)
    assert ws_personal_a not in qs


@pytest.mark.django_db
def test_should_not_see_tenant_workspace_without_tenant_context(
    rf, user_a, ws_tenant_a
):
    """Without tenant context, user_a sees only personal workspaces (tenant_id=None)."""
    request = _make_request(rf, user_a, tenant_id=None)
    qs = _tenant_workspace_qs(request)
    assert ws_tenant_a not in qs


@pytest.mark.django_db
def test_should_see_personal_workspace_without_tenant(
    rf, user_a, ws_personal_a
):
    """User A without tenant context sees own personal workspace."""
    request = _make_request(rf, user_a, tenant_id=None)
    qs = _tenant_workspace_qs(request)
    assert ws_personal_a in qs


@pytest.mark.django_db
def test_should_isolate_all_four_cases(
    rf, user_a, user_b, ws_tenant_a, ws_tenant_b, ws_personal_a
):
    """Full isolation matrix: each context sees exactly the right workspaces."""
    # user_a with TENANT_A
    req = _make_request(rf, user_a, TENANT_A)
    qs = list(_tenant_workspace_qs(req))
    assert ws_tenant_a in qs
    assert ws_tenant_b not in qs
    assert ws_personal_a not in qs

    # user_b with TENANT_B
    req = _make_request(rf, user_b, TENANT_B)
    qs = list(_tenant_workspace_qs(req))
    assert ws_tenant_b in qs
    assert ws_tenant_a not in qs

    # user_a without tenant
    req = _make_request(rf, user_a, None)
    qs = list(_tenant_workspace_qs(req))
    assert ws_personal_a in qs
    assert ws_tenant_a not in qs


# ── HTTP-level isolation via Django test client ───────────────────────────────

@pytest.mark.django_db
def test_should_return_404_for_workspace_of_other_tenant(
    user_a, user_b, ws_tenant_b, client
):
    """User A (no tenant) must get 404 for Workspace that belongs to Tenant B."""
    client.force_login(user_a)
    response = client.get(
        reverse("research:workspace-detail", kwargs={"public_id": ws_tenant_b.public_id})
    )
    assert response.status_code == 404
