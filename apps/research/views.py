"""Research views — HTMX-powered."""
from __future__ import annotations

import os

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from apps.research.forms import ProjectForm, ResearchProjectForm, WorkspaceForm
from apps.research.models import Project, ResearchProject, ResearchResult, Workspace
from apps.research.tasks import run_research_task


def _tenant_workspace_qs(request):
    """Return Workspace queryset filtered by tenant_id if present, else by user."""
    tenant_id = getattr(request, "tenant_id", None)
    qs = Workspace.objects.filter(deleted_at__isnull=True)
    if tenant_id:
        return qs.filter(tenant_id=tenant_id)
    return qs.filter(user=request.user)


# ── Workspace views ─────────────────────────────────────────────────────

class WorkspaceListView(LoginRequiredMixin, ListView):
    model = Workspace
    template_name = "research/workspace_list.html"
    context_object_name = "workspaces"

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
        ctx["projects"] = self.object.projects.filter(
            deleted_at__isnull=True
        ).order_by("-created_at")
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
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ws = self.object.workspace
        ctx["workspace"] = ws
        ctx["researches"] = self.object.researches.filter(
            deleted_at__isnull=True
        ).order_by("-created_at")
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

    def get_queryset(self):
        return ResearchProject.objects.filter(
            workspace__in=_tenant_workspace_qs(self.request),
            deleted_at__isnull=True,
        )


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
        ctx["latest_result"] = self.object.results.order_by("-id").first()
        project = self.object.project
        workspace = self.object.workspace or (
            project.workspace if project else None
        )
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
        html = render_to_string(
            "research/partials/project_status.html", {"project": research}
        )
        return HttpResponse(html)
    return redirect("research:research-detail", public_id=public_id)


def summary_reformat_htmx(request: HttpRequest, public_id: str) -> HttpResponse:
    """HTMX endpoint: reformat existing summary."""
    if request.method != "POST" or request.headers.get("HX-Request") != "true":
        return HttpResponse(status=400)

    research = get_object_or_404(
        ResearchProject,
        public_id=public_id,
        workspace__in=_tenant_workspace_qs(request),
    )
    result = ResearchResult.objects.filter(project=research).order_by("-id").first()
    if not result or not result.summary:
        return HttpResponse("<p class='text-muted'>Keine Zusammenfassung vorhanden.</p>")

    target_format = request.POST.get("target_format", "structured")

    try:
        from authoringfw.text import ReformatTask, TextReformatter

        llm_fn = _make_sync_llm(os.environ.get("TOGETHER_API_KEY", ""))
        reformatter = TextReformatter(llm_fn=llm_fn)
        reformat_result = reformatter.reformat(
            ReformatTask(
                source_text=result.summary,
                target_format=target_format,
                language=research.language or "de",
            )
        )
        reformatted_text = reformat_result.content
    except Exception:  # noqa: BLE001
        reformatted_text = result.summary

    html = render_to_string(
        "research/partials/summary_body.html",
        {"summary": reformatted_text, "target_format": target_format},
        request=request,
    )
    return HttpResponse(html)


def _make_sync_llm(api_key: str):
    """Sync LLM callable wrapping Together AI for TextReformatter."""
    import httpx

    def _call(prompt: str) -> str:
        if not api_key:
            return ""
        resp = httpx.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600,
                "temperature": 0.3,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    return _call
