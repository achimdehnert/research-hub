"""Regression tests for the tenant membership guard (security).

The shared SubdomainTenantMiddleware resolves a tenant from the
``X-Tenant-ID`` header / subdomain without a membership check. The
research-hub middleware must reject a tenant the user is not a member
of, so a user cannot enter a foreign org's context (IDOR).
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django_tenancy.models import Membership, Organization

from apps.tenancy.middleware import ResearchHubTenantMiddleware

User = get_user_model()


def _run(request):
    mw = ResearchHubTenantMiddleware(lambda r: None)
    mw.process_request(request)
    return request


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme", status=Organization.Status.ACTIVE)


@pytest.fixture
def member(db, org):
    user = User.objects.create_user(username="member", password="p", email="m@iil.pet")
    Membership.objects.create(
        organization=org, user=user, tenant_id=org.tenant_id, role=Membership.Role.MEMBER
    )
    return user


@pytest.fixture
def outsider(db):
    return User.objects.create_user(username="outsider", password="p", email="o@iil.pet")


@pytest.mark.django_db
def test_should_honour_tenant_for_member(org, member):
    request = RequestFactory().get("/research/", HTTP_X_TENANT_ID=str(org.tenant_id))
    request.user = member
    _run(request)
    assert request.tenant_id == org.tenant_id


@pytest.mark.django_db
def test_should_reject_tenant_header_for_non_member(org, outsider):
    request = RequestFactory().get("/research/", HTTP_X_TENANT_ID=str(org.tenant_id))
    request.user = outsider
    _run(request)
    assert request.tenant_id is None


@pytest.mark.django_db
def test_should_reject_tenant_header_for_anonymous(org):
    from django.contrib.auth.models import AnonymousUser

    request = RequestFactory().get("/research/", HTTP_X_TENANT_ID=str(org.tenant_id))
    request.user = AnonymousUser()
    _run(request)
    assert request.tenant_id is None
