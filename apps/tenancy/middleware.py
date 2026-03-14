"""Tenant middleware with exempt paths for webhooks/API (ADR-145).

Extends SubdomainTenantMiddleware to skip tenant resolution
for webhook endpoints and other non-tenant paths.
"""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from django_tenancy.middleware import SubdomainTenantMiddleware

EXEMPT_PATH_PREFIXES = (
    "/knowledge/webhook/",
    "/api/",
    "/metrics/",
)


class ResearchHubTenantMiddleware(SubdomainTenantMiddleware):
    """Skip tenant resolution for webhook and API paths."""

    def process_request(
        self, request: HttpRequest,
    ) -> HttpResponse | None:
        path = request.path
        for prefix in EXEMPT_PATH_PREFIXES:
            if path.startswith(prefix):
                request.tenant_id = None
                request.tenant = None
                request.tenant_slug = None
                return None
        return super().process_request(request)
