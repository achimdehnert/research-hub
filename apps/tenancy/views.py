"""Tenancy management views for research-hub."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from django_tenancy.models import Membership, Organization

from apps.tenancy.forms import OrganizationCreateForm


@login_required
def org_list(request: HttpRequest):
    """List organizations the user belongs to."""
    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("organization")
        .order_by("organization__name")
    )
    return render(
        request,
        "tenancy/org_list.html",
        {
            "memberships": memberships,
            "current_tenant": getattr(request, "tenant", None),
        },
    )


@login_required
def org_create(request: HttpRequest):
    """Create a new organization and make the current user owner."""
    form = OrganizationCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                org = Organization.objects.create(
                    name=form.cleaned_data["name"],
                    slug=form.cleaned_data["slug"],
                    status=Organization.Status.TRIAL,
                )
                Membership.objects.create(
                    organization=org,
                    tenant_id=org.tenant_id,
                    user=request.user,
                    role=Membership.Role.OWNER,
                )
            return HttpResponseRedirect(reverse("tenancy:org-list"))
        except IntegrityError:
            # Race: slug taken between clean_slug() check and create
            form.add_error("slug", "Dieser Slug ist bereits vergeben.")
    return render(request, "tenancy/org_create.html", {"form": form})
