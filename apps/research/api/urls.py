from django.urls import path

from apps.research.api import views

urlpatterns = [
    # Workspaces
    path("workspaces/", views.WorkspaceListView.as_view(), name="api-workspace-list"),
    path(
        "workspaces/<uuid:public_id>/",
        views.WorkspaceDetailView.as_view(),
        name="api-workspace-detail",
    ),
    # Projects
    path("projects/", views.ResearchProjectListCreateView.as_view(), name="api-project-list"),
    path(
        "projects/<uuid:public_id>/",
        views.ResearchProjectDetailView.as_view(),
        name="api-project-detail",
    ),
    # Results
    path(
        "results/<uuid:public_id>/",
        views.ResearchResultDetailView.as_view(),
        name="api-result-detail",
    ),
    path(
        "results/<uuid:public_id>/export/",
        views.ResearchResultExportView.as_view(),
        name="api-result-export",
    ),
]
