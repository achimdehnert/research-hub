"""Forms for research app."""

from __future__ import annotations

from django import forms

from apps.research.models import Project, ResearchProject, Workspace


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ["name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class ResearchProjectForm(forms.ModelForm):
    # NOTE: per-source selection (arxiv/pubmed/…) is intentionally NOT a form
    # field. iil_researchfw's ResearchService._academic_results calls
    # AcademicSearchService.search() without forwarding a ``sources`` list and
    # ResearchContext has no such field, so the choice was silently ignored —
    # a misleading UI. Academic search is driven by ``research_type`` alone.
    # Re-add this once iil_researchfw threads ``sources`` through ResearchContext.
    class Meta:
        model = ResearchProject
        fields = [
            "name",
            "query",
            "description",
            "research_type",
            "depth",
            "language",
            "summary_level",
            "citation_style",
            "use_deep_analysis",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "query": forms.Textarea(attrs={"rows": 3}),
        }
