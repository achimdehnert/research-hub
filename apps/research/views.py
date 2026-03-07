"""Research views — HTMX-powered."""
from __future__ import annotations

import os

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from apps.research.forms import ResearchProjectForm
from apps.research.models import ResearchProject, ResearchResult
from apps.research.tasks import run_research_task


class ResearchProjectListView(LoginRequiredMixin, ListView):
    model = ResearchProject
    template_name = "research/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        return ResearchProject.objects.filter(
            user=self.request.user, deleted_at__isnull=True
        )


class ResearchProjectCreateView(LoginRequiredMixin, CreateView):
    model = ResearchProject
    form_class = ResearchProjectForm
    template_name = "research/project_form.html"
    success_url = reverse_lazy("research:project-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        run_research_task.delay(self.object.pk)
        return response


class ResearchProjectDetailView(LoginRequiredMixin, DetailView):
    model = ResearchProject
    template_name = "research/project_detail.html"
    context_object_name = "project"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return ResearchProject.objects.filter(
            user=self.request.user, deleted_at__isnull=True
        ).prefetch_related("results")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["latest_result"] = self.object.results.order_by("-id").first()
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
    """HTMX polling endpoint for project status."""
    project = get_object_or_404(
        ResearchProject, public_id=public_id, user=request.user
    )
    if request.headers.get("HX-Request") == "true":
        html = render_to_string(
            "research/partials/project_status.html", {"project": project}
        )
        return HttpResponse(html)
    return redirect("research:project-detail", public_id=public_id)


def summary_reformat_htmx(request: HttpRequest, public_id: str) -> HttpResponse:
    """HTMX endpoint: reformat existing summary into chosen display format.

    POST params: target_format (compact|bullets|structured|narrative|academic|qa)
    Returns: rendered partial with reformatted summary (no new LLM call for
    simple formats; LLM-backed for complex transformations).
    """
    if request.method != "POST" or request.headers.get("HX-Request") != "true":
        return HttpResponse(status=400)

    project = get_object_or_404(
        ResearchProject, public_id=public_id, user=request.user
    )
    result = ResearchResult.objects.filter(project=project).order_by("-id").first()
    if not result or not result.summary:
        return HttpResponse("<p class='text-muted'>Keine Zusammenfassung vorhanden.</p>")

    target_format = request.POST.get("target_format", "structured")

    try:
        from authoringfw.text import ReformatTask, TextReformatter

        llm_fn = _make_sync_llm(os.environ.get("TOGETHER_API_KEY", ""))
        reformatter = TextReformatter(llm_fn=llm_fn)
        reformat_result = reformatter.reformat(ReformatTask(
            source_text=result.summary,
            target_format=target_format,
            language=project.language or "de",
        ))
        reformatted_text = reformat_result.content
    except Exception:
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
