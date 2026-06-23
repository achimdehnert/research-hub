"""Tenant middleware with exempt paths for webhooks/API (ADR-145).

Extends SubdomainTenantMiddleware to skip tenant resolution
for webhook endpoints and other non-tenant paths, and to enforce
organization membership before any tenant context is honoured.
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse

from django_tenancy.middleware import SubdomainTenantMiddleware

logger = logging.getLogger(__name__)

EXEMPT_PATH_PREFIXES = (
    "/knowledge/",
    "/oidc/",
    "/api/",
    "/metrics/",
    "/livez/",
    "/healthz/",
    "/health/",
)


class ResearchHubTenantMiddleware(SubdomainTenantMiddleware):
    """Skip tenant resolution for webhook/API paths and enforce membership.

    Defense-in-depth: the shared ``SubdomainTenantMiddleware`` resolves a
    tenant from the subdomain *and* the ``X-Tenant-ID`` header WITHOUT
    checking that the requesting user is a member of that organization
    (only its session path verifies membership). Without this guard, any
    user could enter a foreign org's context — and thus see its
    workspaces — by visiting ``acme.<host>`` or sending
    ``X-Tenant-ID: <uuid>``. We re-verify membership here and strip the
    tenant context whenever it is missing.
    """

    def process_request(
        self,
        request: HttpRequest,
    ) -> HttpResponse | None:
        path = request.path
        for prefix in EXEMPT_PATH_PREFIXES:
            if path.startswith(prefix):
                request.tenant_id = None
                request.tenant = None
                request.tenant_slug = None
                return None
        response = super().process_request(request)
        self._enforce_membership(request)
        return response

    @staticmethod
    def _enforce_membership(request: HttpRequest) -> None:
        """Strip the resolved tenant unless the user is a member of it."""
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            return

        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            from django_tenancy.models import Membership

            if Membership.objects.filter(user=user, tenant_id=tenant_id).exists():
                return

        logger.warning(
            "Tenant %s rejected — no membership for user %s (path=%s)",
            tenant_id,
            getattr(user, "pk", None),
            request.path,
        )
        request.tenant_id = None
        request.tenant = None
        request.tenant_slug = None

        # Drop the package's contextvars/RLS binding and any poisoned session
        # value so the rejected tenant cannot leak via async-context or persist.
        try:
            from django_tenancy.context import clear_context

            clear_context()
        except Exception:  # pragma: no cover - context module is optional
            pass
        session = getattr(request, "session", None)
        if session is not None:
            session.pop("_tenant_id", None)
