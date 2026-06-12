"""Tests for Outline webhook rate limiting."""

import pytest
from django.core.cache import cache

from apps.knowledge import views as knowledge_views

WEBHOOK_URL = "/knowledge/webhook/outline/"


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_should_rate_limit_webhook_spam(client, monkeypatch):
    monkeypatch.setattr(knowledge_views, "RATE_LIMIT_MAX", 3)

    statuses = []
    for _ in range(5):
        response = client.post(WEBHOOK_URL, data="{}", content_type="application/json")
        statuses.append(response.status_code)

    # Without a valid HMAC the first requests fail auth (401); past the
    # limit the endpoint short-circuits with 429 before HMAC work.
    assert statuses[:3] == [401, 401, 401]
    assert statuses[3:] == [429, 429]


@pytest.mark.django_db
def test_should_not_rate_limit_normal_traffic(client):
    for _ in range(5):
        response = client.post(WEBHOOK_URL, data="{}", content_type="application/json")
        assert response.status_code == 401
