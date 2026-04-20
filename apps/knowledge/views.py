"""Outline webhook endpoint with HMAC-SHA256 verification.

ADR-145 Phase 9+12: HMAC verification, dedup, lazy secret.
Security: HMAC signature verified before any processing (ADR-050).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from decouple import config

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.knowledge.tasks import (
    delete_knowledge_document_task,
    sync_knowledge_document_task,
)

logger = logging.getLogger(__name__)

DEDUP_TTL = 5  # seconds — Outline fires create+publish simultaneously


def _get_webhook_secret() -> str:
    """Lazy-load secret (allows rotation without restart)."""
    return config("OUTLINE_WEBHOOK_SECRET", default="")

SUPPORTED_EVENTS = {
    "documents.create",
    "documents.update",
    "documents.publish",
    "documents.delete",
    "documents.archive",
}


def _verify_hmac(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Outline webhook.

    Outline sends: t=<timestamp>,s=<hex>
    HMAC is computed over: "{timestamp}.{body}"
    Falls back to sha256=<hex> format for compatibility.
    """
    if not secret or not signature:
        return False

    # Outline format: t=<ts>,s=<hex>
    if signature.startswith("t="):
        parts = dict(
            p.split("=", 1)
            for p in signature.split(",")
            if "=" in p
        )
        ts = parts.get("t", "")
        sig_hex = parts.get("s", "")
        if not ts or not sig_hex:
            return False
        msg = f"{ts}.".encode() + body
        expected = hmac.new(
            secret.encode(), msg, hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, sig_hex)

    # Fallback: sha256=<hex>
    if signature.startswith("sha256="):
        expected = hmac.new(
            secret.encode(), body, hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(
            f"sha256={expected}", signature,
        )

    return False


@csrf_exempt
@require_POST
def outline_webhook(request):
    """Handle Outline webhook events.

    Verifies HMAC-SHA256 signature, then dispatches to Celery tasks.
    Events: documents.create, documents.update, documents.delete.
    """
    signature = (
        request.headers.get("Outline-Signature", "")
        or request.headers.get("X-Outline-Signature", "")
    )

    secret = _get_webhook_secret()
    if not _verify_hmac(request.body, signature, secret):
        logger.warning(
            "Outline webhook: HMAC failed sig=%s secret_set=%s",
            signature[:20] if signature else "EMPTY",
            bool(secret),
        )
        return JsonResponse(
            {"error": "Invalid signature"}, status=401,
        )

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event = payload.get("event", "")

    if event not in SUPPORTED_EVENTS:
        return JsonResponse({"status": "ignored", "event": event})

    # Outline sends: {event, payload: {model: {id, ...}}}
    # Normalize to our format: {event, data: {id, ...}}
    data = payload.get("data") or {}
    if not data:
        outline_payload = payload.get("payload", {})
        model = outline_payload.get("model", {})
        if model:
            data = model
        elif outline_payload.get("id"):
            data = outline_payload
    doc_id = data.get("id")

    if not doc_id:
        logger.warning(
            "Outline webhook: no doc id, keys=%s",
            list(payload.keys()),
        )
        return JsonResponse(
            {"error": "Missing document id"}, status=400,
        )

    # Normalize payload for service layer
    normalized = {
        "event": event,
        "data": data,
    }

    # Dedup: skip if same doc processed within TTL
    # Outline fires create+publish simultaneously
    dedup_key = f"outline_wh:{doc_id}"
    if cache.get(dedup_key):
        logger.debug("Outline webhook: dedup skip %s %s", event, doc_id)
        return JsonResponse({"status": "dedup", "event": event})
    cache.set(dedup_key, 1, DEDUP_TTL)

    if event in ("documents.delete", "documents.archive"):
        delete_knowledge_document_task.delay(str(doc_id))
    else:
        sync_knowledge_document_task.delay(normalized)

    logger.info("Outline webhook: %s for %s", event, doc_id)
    return JsonResponse({"status": "accepted", "event": event})
