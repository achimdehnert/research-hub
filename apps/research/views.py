"""Research views — HTMX-powered."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from apps.research.forms import ResearchProjectForm
from apps.research.models import ResearchProject
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
        return ctx


def project_status_htmx(request: HttpRequest, public_id: str) -> HttpResponse:
    """HTMX polling endpoint for project status."""
    project = get_object_or_404(
        ResearchProject, public_id=public_id, user=request.user
    )
    if request.headers.get("HX-Request") == "true":
        from django.template.loader import render_to_string
        html = render_to_string(
            "research/partials/project_status.html", {"project": project}
        )
        return HttpResponse(html)
    return redirect("research:project-detail", public_id=public_id)
