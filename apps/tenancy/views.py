"""Tenancy management views for research-hub."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from django_tenancy.models import Membership, Organization


@login_required
def org_list(request: HttpRequest):
    """List organizations the user belongs to."""
    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("organization")
        .order_by("organization__name")
    )
    return render(request, "tenancy/org_list.html", {
        "memberships": memberships,
        "current_tenant": getattr(request, "tenant", None),
    })


@login_required
def org_create(request: HttpRequest):
    """Create a new organization and make the current user owner."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        slug = request.POST.get("slug", "").strip()
        if name and slug:
            org = Organization.objects.create(
                name=name,
                slug=slug,
                status=Organization.Status.TRIAL,
            )
            Membership.objects.create(
                organization=org,
                tenant_id=org.tenant_id,
                user=request.user,
                role=Membership.Role.OWNER,
            )
            return HttpResponseRedirect(reverse("tenancy:org-list"))
    return render(request, "tenancy/org_create.html", {})
