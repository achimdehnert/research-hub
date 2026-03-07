from django.urls import path
from apps.research.api import views

urlpatterns = [
    path("projects/", views.ResearchProjectListCreateView.as_view(), name="api-project-list"),
    path("projects/<uuid:public_id>/", views.ResearchProjectDetailView.as_view(), name="api-project-detail"),
]
