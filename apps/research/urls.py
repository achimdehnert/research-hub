from django.urls import path

from apps.research import views

app_name = "research"

urlpatterns = [
    # Workspace
    path("", views.WorkspaceListView.as_view(), name="workspace-list"),
    path("workspaces/new/", views.WorkspaceCreateView.as_view(), name="workspace-create"),
    path(
        "workspaces/<uuid:public_id>/",
        views.WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
    # Research Projects (Recherchen)
    path("projects/", views.ResearchProjectListView.as_view(), name="project-list"),
    path("projects/new/", views.ResearchProjectCreateView.as_view(), name="project-create"),
    path(
        "projects/<uuid:public_id>/",
        views.ResearchProjectDetailView.as_view(),
        name="project-detail",
    ),
    path(
        "projects/<uuid:public_id>/status/",
        views.project_status_htmx,
        name="project-status",
    ),
    path(
        "projects/<uuid:public_id>/reformat/",
        views.summary_reformat_htmx,
        name="summary-reformat",
    ),
]
