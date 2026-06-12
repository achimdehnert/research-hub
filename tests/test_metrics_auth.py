"""Tests for metrics endpoint auth — query-param tokens must NOT work."""

import pytest
from django.contrib.auth import get_user_model

from apps.research import views_metrics

User = get_user_model()


@pytest.fixture
def metrics_token(monkeypatch):
    monkeypatch.setattr(views_metrics, "METRICS_TOKEN", "s3cret")
    return "s3cret"


@pytest.mark.django_db
def test_should_reject_query_param_token(client, metrics_token):
    """Query-param tokens leak into access logs — removed deliberately."""
    response = client.get("/metrics/", {"token": metrics_token})
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_should_accept_bearer_token(client, metrics_token):
    response = client.get("/metrics/", HTTP_AUTHORIZATION=f"Bearer {metrics_token}")
    assert response.status_code == 200


@pytest.mark.django_db
def test_should_reject_anonymous(client):
    response = client.get("/metrics/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_should_accept_staff_session(client):
    staff = User.objects.create_user(
        username="metrics_staff", password="pass", email="ms@iil.pet", is_staff=True
    )
    client.force_login(staff)
    response = client.get("/metrics/")
    assert response.status_code == 200
