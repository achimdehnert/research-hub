"""Tests for list pagination — research list and knowledge dashboard."""

import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.knowledge.models import KnowledgeDocument
from apps.research.models import ResearchProject, Workspace

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="page_user", password="pass", email="page@iil.pet")


@pytest.fixture
def staff(db):
    return User.objects.create_user(
        username="page_staff", password="pass", email="staff@iil.pet", is_staff=True
    )


@pytest.mark.django_db
def test_should_paginate_research_list(user, client):
    workspace = Workspace.objects.create(user=user, name="Page WS")
    for i in range(30):
        ResearchProject.objects.create(
            user=user, workspace=workspace, name=f"Recherche {i}", query="q"
        )

    client.force_login(user)
    page1 = client.get("/research/research/")
    assert page1.status_code == 200
    assert len(page1.context["researches"]) == 24
    assert page1.context["page_obj"].paginator.num_pages == 2

    page2 = client.get("/research/research/", {"page": 2})
    assert len(page2.context["researches"]) == 6


@pytest.mark.django_db
def test_should_paginate_knowledge_dashboard(staff, client):
    for i in range(60):
        KnowledgeDocument.objects.create(outline_id=uuid.uuid4(), title=f"Doc {i}")

    client.force_login(staff)
    page1 = client.get("/knowledge/dashboard/")
    assert page1.status_code == 200
    assert len(page1.context["documents"]) == 50

    page2 = client.get("/knowledge/dashboard/", {"page": 2})
    assert len(page2.context["documents"]) == 10


@pytest.mark.django_db
def test_should_keep_filters_in_pagination_links(staff, client):
    for i in range(60):
        KnowledgeDocument.objects.create(outline_id=uuid.uuid4(), title=f"Findable {i}")

    client.force_login(staff)
    response = client.get("/knowledge/dashboard/", {"q": "Findable"})
    assert response.status_code == 200
    assert "q=Findable" in response.context["base_query"]
