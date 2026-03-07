from django.urls import path

from apps.research import views

app_name = "research"

urlpatterns = [
    path("", views.ResearchProjectListView.as_view(), name="project-list"),
    path("new/", views.ResearchProjectCreateView.as_view(), name="project-create"),
    path("<uuid:public_id>/", views.ResearchProjectDetailView.as_view(), name="project-detail"),
    path("<uuid:public_id>/status/", views.project_status_htmx, name="project-status"),
]
