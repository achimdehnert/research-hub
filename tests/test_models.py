import pytest
from django.contrib.auth import get_user_model
from apps.research.models import ResearchProject

User = get_user_model()


@pytest.mark.django_db
def test_research_project_create(db):
    user = User.objects.create_user(username="testuser", password="pass", email="test@iil.pet")
    project = ResearchProject.objects.create(
        user=user, name="Test Project", query="machine learning"
    )
    assert project.public_id is not None
    assert project.status == "draft"
    assert str(project) == "Test Project"
