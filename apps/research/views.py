"""Research views — HTMX-powered."""

from __future__ import annotations

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from apps.research.forms import ProjectForm, ResearchProjectForm, WorkspaceForm
from apps.research.models import Project, ResearchProject, ResearchResult, Workspace
from apps.research.soft_delete import (
    soft_delete_project,
    soft_delete_research,
    soft_delete_workspace as soft_delete_workspace_cascade,
)
from apps.research.tasks import (
    REFORMAT_CACHE_TTL,
    reformat_summary_task,
    run_research_task,
)

REFORMAT_FORMATS = {"structured", "bullets", "compact", "narrative", "academic", "qa"}


def _tenant_workspace_qs(request):
    """Return Workspace queryset filtered by tenant_id if present, else by user."""
    tenant_id = getattr(request, "tenant_id", None)
    qs = Workspace.objects.filter(deleted_at__isnull=True)
    if tenant_id:
        return qs.filter(tenant_id=tenant_id)
    return qs.filter(user=request.user, tenant_id__isnull=True)


# ── Workspace views ─────────────────────────────────────────────────────


class WorkspaceListView(LoginRequiredMixin, ListView):
    model = Workspace
    template_name = "research/workspace_list.html"
    context_object_name = "workspaces"
    paginate_by = 24

    def get_queryset(self):
        return _tenant_workspace_qs(self.request).prefetch_related("projects")


class WorkspaceCreateView(LoginRequiredMixin, CreateView):
    model = Workspace
    form_class = WorkspaceForm
    template_name = "research/workspace_form.html"
    success_url = reverse_lazy("research:workspace-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        tenant_id = getattr(self.request, "tenant_id", None)
        if tenant_id:
            form.instance.tenant_id = tenant_id
        return super().form_valid(form)


class WorkspaceDetailView(LoginRequiredMixin, DetailView):
    model = Workspace
    template_name = "research/workspace_detail.html"
    context_object_name = "workspace"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return _tenant_workspace_qs(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = self.object.projects.filter(deleted_at__isnull=True).order_by(
            "-created_at"
        )
        ctx["breadcrumb"] = [
            {"label": "Workspaces", "url": reverse_lazy("research:workspace-list")},
            {"label": self.object.name, "url": ""},
        ]
        return ctx


# ── Project views ──────────────────────────────────────────────────────


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "research/project_form.html"

    def _get_workspace(self):
        return get_object_or_404(
            _tenant_workspace_qs(self.request),
            public_id=self.kwargs["workspace_id"],
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ws = self._get_workspace()
        ctx["workspace"] = ws
        ctx["breadcrumb"] = [
            {"label": "Workspaces", "url": reverse_lazy("research:workspace-list")},
            {"label": ws.name, "url": ws.get_absolute_url()},
            {"label": "Neues Projekt", "url": ""},
        ]
        return ctx

    def form_valid(self, form):
        ws = self._get_workspace()
        form.instance.user = self.request.user
        form.instance.workspace = ws
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.workspace.get_absolute_url()


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "research/project_detail.html"
    context_object_name = "project"
    slug_field = "public_id"
    slug_url_kwarg = "project_id"

    def get_queryset(self):
        return Project.objects.filter(
            workspace__in=_tenant_workspace_qs(self.request),
            deleted_at__isnull=True,
        ).select_related("workspace")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ws = self.object.workspace
        ctx["workspace"] = ws
        ctx["researches"] = self.object.researches.filter(deleted_at__isnull=True).order_by(
            "-created_at"
        )
        ctx["breadcrumb"] = [
            {"label": "Workspaces", "url": reverse_lazy("research:workspace-list")},
            {"label": ws.name, "url": ws.get_absolute_url()},
            {"label": self.object.name, "url": ""},
        ]
        return ctx


# ── ResearchProject (Recherche) views ────────────────────────────────


class ResearchProjectListView(LoginRequiredMixin, ListView):
    model = ResearchProject
    template_name = "research/research_list.html"
    context_object_name = "researches"
    paginate_by = 24

    def get_queryset(self):
        return ResearchProject.objects.filter(
            workspace__in=_tenant_workspace_qs(self.request),
            deleted_at__isnull=True,
        ).select_related("workspace", "project", "project__workspace")


class ResearchProjectCreateView(LoginRequiredMixin, CreateView):
    model = ResearchProject
    form_class = ResearchProjectForm
    template_name = "research/research_form.html"
    success_url = reverse_lazy("research:workspace-list")

    def _get_project(self):
        """Resolve project from GET or POST — checks all possible key names."""
        project_id = (
            self.request.GET.get("project")
            or self.request.POST.get("project_id")
            or self.request.POST.get("project")
        )
        if project_id:
            try:
                return Project.objects.get(
                    public_id=project_id,
                    workspace__in=_tenant_workspace_qs(self.request),
                )
            except Project.DoesNotExist:
                pass
        return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self._get_project()
        if project:
            ctx["project"] = project
            ctx["workspace"] = project.workspace
            ctx["breadcrumb"] = [
                {"label": "Workspaces", "url": reverse_lazy("research:workspace-list")},
                {"label": project.workspace.name, "url": project.workspace.get_absolute_url()},
                {"label": project.name, "url": project.get_absolute_url()},
                {"label": "Neue Recherche", "url": ""},
            ]
        return ctx

    def form_valid(self, form):
        form.instance.user = self.request.user
        project = self._get_project()
        if project:
            form.instance.project = project
            form.instance.workspace = project.workspace
        response = super().form_valid(form)
        run_research_task.delay(self.object.pk)
        return response

    def get_success_url(self):
        if self.object.project:
            return self.object.project.get_absolute_url()
        return str(reverse_lazy("research:workspace-list"))


class ResearchProjectDetailView(LoginRequiredMixin, DetailView):
    model = ResearchProject
    template_name = "research/research_detail.html"
    context_object_name = "research"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return ResearchProject.objects.filter(
            workspace__in=_tenant_workspace_qs(self.request),
            deleted_at__isnull=True,
        ).prefetch_related("results")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["latest_result"] = (
            self.object.results.filter(deleted_at__isnull=True).order_by("-id").first()
        )
        project = self.object.project
        workspace = self.object.workspace or (project.workspace if project else None)
        ctx["project"] = project
        ctx["workspace"] = workspace
        if project and workspace:
            ctx["breadcrumb"] = [
                {"label": "Workspaces", "url": reverse_lazy("research:workspace-list")},
                {"label": workspace.name, "url": workspace.get_absolute_url()},
                {"label": project.name, "url": project.get_absolute_url()},
                {"label": self.object.name, "url": ""},
            ]
        ctx["reformat_formats"] = [
            ("structured", "Strukturiert", "layout-text-sidebar"),
            ("bullets", "Stichpunkte", "list-ul"),
            ("compact", "Kompakt", "text-paragraph"),
            ("narrative", "Fließtext", "file-text"),
            ("academic", "Abstract", "journal-text"),
            ("qa", "FAQ", "question-circle"),
        ]
        return ctx


def project_status_htmx(request: HttpRequest, public_id: str) -> HttpResponse:
    """HTMX polling endpoint for research status."""
    research = get_object_or_404(
        ResearchProject,
        public_id=public_id,
        workspace__in=_tenant_workspace_qs(request),
    )
    if request.headers.get("HX-Request") == "true":
        html = render_to_string("research/partials/project_status.html", {"project": research})
        return HttpResponse(html)
    return redirect("research:research-detail", public_id=public_id)


def summary_reformat_htmx(request: HttpRequest, public_id: str) -> HttpResponse:
    """HTMX endpoint: dispatch summary reformat to Celery, return polling partial.

    The LLM call runs in a worker — the request never blocks on it. The
    result lands in the cache under a one-shot key the polling endpoint reads.
    """
    if request.method != "POST" or request.headers.get("HX-Request") != "true":
        return HttpResponse(status=400)

    research = get_object_or_404(
        ResearchProject,
        public_id=public_id,
        workspace__in=_tenant_workspace_qs(request),
    )
    result = (
        ResearchResult.objects.filter(project=research, deleted_at__isnull=True)
        .order_by("-id")
        .first()
    )
    if not result or not result.summary:
        return HttpResponse("<p class='text-muted'>Keine Zusammenfassung vorhanden.</p>")

    target_format = request.POST.get("target_format", "structured")
    if target_format not in REFORMAT_FORMATS:
        return HttpResponse(status=400)

    cache_key = f"reformat:{result.pk}:{target_format}:{uuid.uuid4().hex[:12]}"
    cache.set(cache_key, {"status": "pending"}, REFORMAT_CACHE_TTL)
    reformat_summary_task.delay(result.pk, target_format, research.language or "de", cache_key)

    html = render_to_string(
        "research/partials/summary_reformat_pending.html",
        {"research": research, "reformat_key": cache_key},
        request=request,
    )
    return HttpResponse(html)


def summary_reformat_status(request: HttpRequest, public_id: str) -> HttpResponse:
    """HTMX polling endpoint: return reformatted summary once the task finished."""
    research = get_object_or_404(
        ResearchProject,
        public_id=public_id,
        workspace__in=_tenant_workspace_qs(request),
    )
    result = (
        ResearchResult.objects.filter(project=research, deleted_at__isnull=True)
        .order_by("-id")
        .first()
    )
    cache_key = request.GET.get("key", "")
    # Key must belong to this (tenant-checked) research's result — no cache probing
    if not result or not cache_key.startswith(f"reformat:{result.pk}:"):
        return HttpResponse(status=400)

    data = cache.get(cache_key)
    if data is None:
        return HttpResponse(
            "<p class='text-muted'>Formatierung abgelaufen — bitte erneut versuchen.</p>"
        )
    if data.get("status") != "done":
        html = render_to_string(
            "research/partials/summary_reformat_pending.html",
            {"research": research, "reformat_key": cache_key},
            request=request,
        )
        return HttpResponse(html)

    cache.delete(cache_key)
    html = render_to_string(
        "research/partials/summary_body.html",
        {"summary": data.get("summary", ""), "target_format": data.get("target_format")},
        request=request,
    )
    return HttpResponse(html)


# ── Soft-delete views ──────────────────────────────────────────────────


@login_required
@require_POST
def workspace_delete(request: HttpRequest, public_id: str) -> HttpResponse:
    """Soft-delete a workspace including its projects and researches."""
    workspace = get_object_or_404(_tenant_workspace_qs(request), public_id=public_id)
    soft_delete_workspace_cascade(workspace)
    messages.success(request, f"Workspace „{workspace.name}“ wurde gelöscht.")
    return redirect("research:workspace-list")


@login_required
@require_POST
def project_delete(request: HttpRequest, project_id: str) -> HttpResponse:
    """Soft-delete a project including its researches."""
    project = get_object_or_404(
        Project.objects.filter(
            workspace__in=_tenant_workspace_qs(request),
            deleted_at__isnull=True,
        ).select_related("workspace"),
        public_id=project_id,
    )
    soft_delete_project(project)
    messages.success(request, f"Projekt „{project.name}“ wurde gelöscht.")
    return redirect(project.workspace.get_absolute_url())


@login_required
@require_POST
def research_delete(request: HttpRequest, public_id: str) -> HttpResponse:
    """Soft-delete a single research."""
    research = get_object_or_404(
        ResearchProject.objects.filter(
            workspace__in=_tenant_workspace_qs(request),
            deleted_at__isnull=True,
        ).select_related("project"),
        public_id=public_id,
    )
    soft_delete_research(research)
    messages.success(request, f"Recherche „{research.name}“ wurde gelöscht.")
    if research.project:
        return redirect(research.project.get_absolute_url())
    return redirect("research:workspace-list")
