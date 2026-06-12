"""Tests for organization creation — validation + duplicate slug handling."""

import pytest
from django.contrib.auth import get_user_model

from django_tenancy.models import Membership, Organization

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="org_user", password="pass", email="org@iil.pet")


@pytest.mark.django_db
def test_should_create_org_with_owner_membership(user, client):
    client.force_login(user)
    response = client.post("/tenancy/create/", {"name": "Acme GmbH", "slug": "acme"})
    assert response.status_code == 302

    org = Organization.objects.get(slug="acme")
    assert Membership.objects.filter(
        organization=org, user=user, role=Membership.Role.OWNER
    ).exists()


@pytest.mark.django_db
def test_should_show_error_for_duplicate_slug(user, client):
    Organization.objects.create(name="First", slug="taken", status=Organization.Status.TRIAL)
    client.force_login(user)
    response = client.post("/tenancy/create/", {"name": "Second", "slug": "taken"})
    assert response.status_code == 200
    assert "bereits vergeben" in response.content.decode()
    assert Organization.objects.filter(slug="taken").count() == 1


@pytest.mark.django_db
def test_should_reject_invalid_slug(user, client):
    client.force_login(user)
    response = client.post("/tenancy/create/", {"name": "Bad", "slug": "Bad Slug!"})
    assert response.status_code == 200
    assert Organization.objects.filter(name="Bad").count() == 0


@pytest.mark.django_db
def test_should_keep_submitted_values_on_error(user, client):
    Organization.objects.create(name="First", slug="taken", status=Organization.Status.TRIAL)
    client.force_login(user)
    response = client.post("/tenancy/create/", {"name": "Meine Firma", "slug": "taken"})
    assert "Meine Firma" in response.content.decode()
