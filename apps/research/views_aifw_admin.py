"""Frontend aifw dashboard — staff-only overview of providers, models, actions, usage."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from decouple import config

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone


@staff_member_required
def aifw_dashboard(request: HttpRequest) -> HttpResponse:
    """Main aifw admin dashboard."""
    from aifw.models import (
        AIActionType,
        AIUsageLog,
        LLMModel,
        LLMProvider,
    )

    # ── Providers with API key status ──
    providers = []
    for p in LLMProvider.objects.all():
        key_env = p.api_key_env_var or ""
        key_value = config(key_env, default="") if key_env else ""
        providers.append(
            {
                "obj": p,
                "key_env": key_env,
                "key_set": bool(key_value),
                "key_preview": (
                    f"{key_value[:4]}...{key_value[-4:]}" if len(key_value) > 8 else ""
                ),
                "model_count": LLMModel.objects.filter(provider=p).count(),
            }
        )

    # ── Models ──
    models = LLMModel.objects.select_related("provider").order_by("provider__name", "name")

    # ── Actions ──
    actions = AIActionType.objects.select_related(
        "default_model",
        "default_model__provider",
        "fallback_model",
        "fallback_model__provider",
    ).order_by("code")

    # ── Usage stats (last 7 days) ──
    since = timezone.now() - timedelta(days=7)
    usage_qs = AIUsageLog.objects.filter(created_at__gte=since)
    agg = usage_qs.aggregate(
        total_tokens=Sum("total_tokens"),
        total_cost=Sum("estimated_cost"),
    )
    usage_stats = {
        "total_calls": usage_qs.count(),
        "total_tokens": agg["total_tokens"] or 0,
        "total_cost": agg["total_cost"] or Decimal("0.00"),
        "success_count": usage_qs.filter(success=True).count(),
        "error_count": usage_qs.filter(success=False).count(),
    }

    # ── Per-action usage breakdown ──
    action_usage = (
        usage_qs.values("action_type__code", "action_type__name")
        .annotate(
            calls=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost"),
        )
        .order_by("-calls")
    )

    # ── Recent errors ──
    recent_errors = (
        usage_qs.filter(success=False)
        .select_related("action_type", "model_used")
        .order_by("-created_at")[:5]
    )

    return render(
        request,
        "research/aifw_dashboard.html",
        {
            "providers": providers,
            "models": models,
            "actions": actions,
            "usage_stats": usage_stats,
            "action_usage": action_usage,
            "recent_errors": recent_errors,
            "breadcrumb": [
                {"label": "aifw Dashboard", "url": ""},
            ],
        },
    )


@staff_member_required
def aifw_toggle_action(request: HttpRequest) -> HttpResponse:
    """HTMX: toggle is_active on an AIActionType."""
    if request.method != "POST":
        return HttpResponse(status=405)

    from aifw.models import AIActionType

    action_id = request.POST.get("action_id")
    try:
        action = AIActionType.objects.get(pk=action_id)
        action.is_active = not action.is_active
        action.save(update_fields=["is_active"])
        icon = "check-circle-fill" if action.is_active else "x-circle"
        color = "#4ade80" if action.is_active else "#f87171"
        return HttpResponse(
            f'<span style="color:{color}">'
            f'<i class="bi bi-{icon}"></i> '
            f"{'Aktiv' if action.is_active else 'Inaktiv'}"
            f"</span>"
        )
    except AIActionType.DoesNotExist:
        return HttpResponse("Not found", status=404)


@staff_member_required
def aifw_toggle_provider(request: HttpRequest) -> HttpResponse:
    """HTMX: toggle is_active on an LLMProvider."""
    if request.method != "POST":
        return HttpResponse(status=405)

    from aifw.models import LLMProvider

    provider_id = request.POST.get("provider_id")
    try:
        provider = LLMProvider.objects.get(pk=provider_id)
        provider.is_active = not provider.is_active
        provider.save(update_fields=["is_active"])
        icon = "check-circle-fill" if provider.is_active else "x-circle"
        color = "#4ade80" if provider.is_active else "#f87171"
        return HttpResponse(
            f'<span style="color:{color}">'
            f'<i class="bi bi-{icon}"></i> '
            f"{'Aktiv' if provider.is_active else 'Inaktiv'}"
            f"</span>"
        )
    except LLMProvider.DoesNotExist:
        return HttpResponse("Not found", status=404)
