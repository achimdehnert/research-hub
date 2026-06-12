"""Forms for tenancy management."""

from __future__ import annotations

from django import forms
from django.core.validators import RegexValidator

from django_tenancy.models import Organization


class OrganizationCreateForm(forms.Form):
    name = forms.CharField(max_length=255, label="Name")
    slug = forms.CharField(
        max_length=63,
        label="Subdomain-Slug",
        validators=[
            RegexValidator(
                r"^[a-z0-9]+(-[a-z0-9]+)*$",
                "Nur Kleinbuchstaben, Zahlen und Bindestriche (nicht am Anfang/Ende).",
            )
        ],
    )

    def clean_slug(self) -> str:
        slug = self.cleaned_data["slug"]
        if Organization.objects.filter(slug=slug).exists():
            raise forms.ValidationError("Dieser Slug ist bereits vergeben.")
        return slug
