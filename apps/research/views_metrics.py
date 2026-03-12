"""Monitoring metrics endpoint — JSON + Prometheus text format.

Exposes:
- aifw usage (calls, tokens, cost per action/provider)
- Celery task stats (running, succeeded, failed)
- Research project counts by status
- System health checks (DB, Redis, content-store)

Access: staff-only (JSON) or token-auth for Prometheus scraping.
"""
from __future__ import annotations

import os
import time
from datetime import timedelta

from django.db import connections
from django.db.models import Count, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt


METRICS_TOKEN = os.environ.get("METRICS_TOKEN", "")


def _check_auth(request: HttpRequest) -> bool:
    """Allow staff users or token-based auth for scrapers."""
    if hasattr(request, "user") and request.user.is_authenticated:
        if request.user.is_staff:
            return True
    token = request.GET.get("token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if METRICS_TOKEN and token == METRICS_TOKEN:
        return True
    return False


def _health_checks() -> dict:
    """Run DB, Redis, content-store connectivity checks."""
    checks = {}

    # Default DB
    try:
        t0 = time.monotonic()
        conn = connections["default"]
        conn.ensure_connection()
        with conn.cursor() as c:
            c.execute("SELECT 1")
        checks["db"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as e:
        checks["db"] = {"status": "error", "error": str(e)}

    # Redis
    try:
        from config.celery import app as celery_app
        t0 = time.monotonic()
        celery_app.connection_for_read().ensure_connection(
            max_retries=1, timeout=2,
        )
        checks["redis"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)}

    # Content-store DB
    try:
        t0 = time.monotonic()
        conn = connections["content_store"]
        conn.ensure_connection()
        with conn.cursor() as c:
            c.execute("SELECT 1")
        checks["content_store"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as e:
        checks["content_store"] = {
            "status": "error", "error": str(e),
        }

    return checks


def _aifw_metrics(days: int = 7) -> dict:
    """Aggregate aifw usage metrics."""
    try:
        from aifw.models import AIUsageLog, LLMProvider
    except ImportError:
        return {}

    since = timezone.now() - timedelta(days=days)
    qs = AIUsageLog.objects.filter(created_at__gte=since)

    agg = qs.aggregate(
        total_tokens=Sum("total_tokens"),
        total_cost=Sum("estimated_cost"),
    )

    # Per-action breakdown
    by_action = list(
        qs.values("action_type__code")
        .annotate(
            calls=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost"),
        )
        .order_by("-calls")
    )

    # Per-provider breakdown
    by_provider = list(
        qs.values("model_used__provider__name")
        .annotate(
            calls=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost"),
        )
        .order_by("-calls")
    )

    # Provider status
    providers = {}
    for p in LLMProvider.objects.all():
        key = os.environ.get(p.api_key_env_var or "", "")
        providers[p.name] = {
            "active": p.is_active,
            "key_set": bool(key),
        }

    return {
        "period_days": days,
        "total_calls": qs.count(),
        "total_tokens": agg["total_tokens"] or 0,
        "total_cost": float(agg["total_cost"] or 0),
        "success_count": qs.filter(success=True).count(),
        "error_count": qs.filter(success=False).count(),
        "by_action": [
            {
                "action": r["action_type__code"],
                "calls": r["calls"],
                "tokens": r["tokens"] or 0,
                "cost": float(r["cost"] or 0),
            }
            for r in by_action
        ],
        "by_provider": [
            {
                "provider": r["model_used__provider__name"],
                "calls": r["calls"],
                "tokens": r["tokens"] or 0,
                "cost": float(r["cost"] or 0),
            }
            for r in by_provider
        ],
        "providers": providers,
    }


def _research_metrics() -> dict:
    """Research project counts by status."""
    from apps.research.models import ResearchProject

    by_status = dict(
        ResearchProject.objects.values_list("status")
        .annotate(c=Count("id"))
        .values_list("status", "c")
    )
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
    }


def _celery_metrics() -> dict:
    """Celery task metrics from django-celery-results."""
    try:
        from django_celery_results.models import TaskResult
    except ImportError:
        return {}

    since = timezone.now() - timedelta(days=7)
    qs = TaskResult.objects.filter(date_done__gte=since)
    by_status = dict(
        qs.values_list("status")
        .annotate(c=Count("id"))
        .values_list("status", "c")
    )
    return {
        "period_days": 7,
        "total": qs.count(),
        "by_status": by_status,
    }


def _content_store_metrics() -> dict:
    """Content-store item counts."""
    try:
        from content_store.models import ContentItem
        qs = ContentItem.objects.using("content_store")
        by_type = dict(
            qs.values_list("type")
            .annotate(c=Count("id"))
            .values_list("type", "c")
        )
        return {
            "total": qs.count(),
            "by_type": by_type,
        }
    except Exception:
        return {}


def _to_prometheus(data: dict) -> str:
    """Convert metrics dict to Prometheus text exposition format."""
    lines = []

    def _add(
        name: str, value,
        help_text: str = "",
        labels: dict | None = None,
    ):
        if help_text and not any(
            ln.startswith(f"# HELP {name}")
            for ln in lines
        ):
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} gauge")
        label_str = ""
        if labels:
            parts = [f'{k}="{v}"' for k, v in labels.items()]
            label_str = "{" + ",".join(parts) + "}"
        lines.append(f"{name}{label_str} {value}")

    # Health
    health = data.get("health", {})
    for svc, info in health.items():
        ok = 1 if info.get("status") == "ok" else 0
        _add(
            "research_health_up", ok,
            "Service health status (1=ok, 0=error)",
            {"service": svc},
        )
        if "latency_ms" in info:
            _add(
                "research_health_latency_ms",
                info["latency_ms"],
                "Health check latency in ms",
                {"service": svc},
            )

    # aifw
    aifw = data.get("aifw", {})
    _add(
        "aifw_calls_total", aifw.get("total_calls", 0),
        "Total aifw LLM calls",
    )
    _add(
        "aifw_tokens_total", aifw.get("total_tokens", 0),
        "Total tokens used",
    )
    _add(
        "aifw_cost_total", aifw.get("total_cost", 0),
        "Total estimated cost in USD",
    )
    _add(
        "aifw_success_total", aifw.get("success_count", 0),
        "Successful aifw calls",
    )
    _add(
        "aifw_error_total", aifw.get("error_count", 0),
        "Failed aifw calls",
    )
    for a in aifw.get("by_action", []):
        _add(
            "aifw_action_calls",
            a["calls"],
            "Calls per action",
            {"action": a["action"]},
        )
        _add(
            "aifw_action_tokens",
            a["tokens"],
            "Tokens per action",
            {"action": a["action"]},
        )

    for p in aifw.get("by_provider", []):
        _add(
            "aifw_provider_calls",
            p["calls"],
            "Calls per provider",
            {"provider": p["provider"]},
        )

    # Research
    research = data.get("research", {})
    _add(
        "research_projects_total",
        research.get("total", 0),
        "Total research projects",
    )
    for status, count in research.get("by_status", {}).items():
        _add(
            "research_projects_by_status",
            count,
            "Projects by status",
            {"status": status},
        )

    # Content-store
    cs = data.get("content_store", {})
    _add(
        "content_store_items_total",
        cs.get("total", 0),
        "Total content-store items",
    )

    lines.append("")
    return "\n".join(lines)


@csrf_exempt
@never_cache
def metrics_json(request: HttpRequest) -> HttpResponse:
    """JSON metrics endpoint — staff or token auth."""
    if not _check_auth(request):
        return JsonResponse(
            {"error": "unauthorized"}, status=401,
        )

    data = {
        "ts": timezone.now().isoformat(),
        "service": "research-hub",
        "health": _health_checks(),
        "aifw": _aifw_metrics(),
        "research": _research_metrics(),
        "celery": _celery_metrics(),
        "content_store": _content_store_metrics(),
    }
    return JsonResponse(data)


@csrf_exempt
@never_cache
def metrics_prometheus(request: HttpRequest) -> HttpResponse:
    """Prometheus text exposition format endpoint."""
    if not _check_auth(request):
        return HttpResponse("unauthorized\n", status=401)

    data = {
        "health": _health_checks(),
        "aifw": _aifw_metrics(),
        "research": _research_metrics(),
        "celery": _celery_metrics(),
        "content_store": _content_store_metrics(),
    }
    body = _to_prometheus(data)
    return HttpResponse(
        body,
        content_type=(
            "text/plain; version=0.0.4; charset=utf-8"
        ),
    )
