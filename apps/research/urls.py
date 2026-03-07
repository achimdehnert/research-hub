from django.urls import path

from apps.research import views

app_name = "research"

urlpatterns = [
    # Workspaces
    path("", views.WorkspaceListView.as_view(), name="workspace-list"),
    path("workspaces/new/", views.WorkspaceCreateView.as_view(), name="workspace-create"),
    path(
        "workspaces/<uuid:public_id>/",
        views.WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
    # Projects (nested under workspace)
    path(
        "workspaces/<uuid:workspace_id>/projects/new/",
        views.ProjectCreateView.as_view(),
        name="project-create",
    ),
    path(
        "projects/<uuid:project_id>/",
        views.ProjectDetailView.as_view(),
        name="project-detail",
    ),
    # Recherchen (nested under project)
    path(
        "research/new/",
        views.ResearchProjectCreateView.as_view(),
        name="research-create",
    ),
    path(
        "research/<uuid:public_id>/",
        views.ResearchProjectDetailView.as_view(),
        name="research-detail",
    ),
    path(
        "research/<uuid:public_id>/status/",
        views.project_status_htmx,
        name="research-status",
    ),
    path(
        "research/<uuid:public_id>/reformat/",
        views.summary_reformat_htmx,
        name="summary-reformat",
    ),
    # Legacy aliases
    path("projects/", views.ResearchProjectListView.as_view(), name="project-list"),
    path("projects/new/", views.ResearchProjectCreateView.as_view(), name="project-create-legacy"),
    path(
        "projects/<uuid:public_id>/",
        views.ResearchProjectDetailView.as_view(),
        name="project-detail-legacy",
    ),
]
