"""Forms for research app."""
from __future__ import annotations

from django import forms

from apps.research.models import ResearchProject


class ResearchProjectForm(forms.ModelForm):
    academic_sources = forms.MultipleChoiceField(
        choices=ResearchProject.ACADEMIC_SOURCE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        initial=["arxiv", "semantic_scholar", "pubmed", "openalex"],
        label="Akademische Quellen",
    )

    class Meta:
        model = ResearchProject
        fields = [
            "name",
            "query",
            "description",
            "research_type",
            "depth",
            "academic_sources",
            "language",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "query": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_academic_sources(self) -> list[str]:
        return self.cleaned_data.get("academic_sources") or []
