"""
Webhook service for OSS hybrid integrations (Activepieces, Chatwoot, external systems).
Dispatches signed POSTs on events. Configured via DB webhooks table (admin UI manages).
Zero extra cost; uses stdlib + requests if available (graceful fallback).
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Optional

import requests  # type: ignore  # may not be in minimal; fallback to urllib if missing

from sqlalchemy.orm import Session

from apps.api.config import settings
from infrastructure.db.models.webhook import Webhook

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.timeout = settings.WEBHOOK_TIMEOUT_SEC

    def dispatch(self, event: str, payload: dict[str, Any]) -> int:
        """Fire matching active webhooks for the event. Returns count dispatched (best effort)."""
        hooks = self.db.query(Webhook).filter(Webhook.active == True).all()  # noqa: E712
        dispatched = 0
        full_payload = {
            "event": event,
            "timestamp": int(time.time()),
            "data": payload,
        }
        body = json.dumps(full_payload, separators=(",", ":"), default=str).encode("utf-8")

        for hook in hooks:
            events = hook.events or []
            if isinstance(events, str):
                try:
                    events = json.loads(events)
                except Exception:
                    events = []
            if event not in events and "*" not in events:
                continue
            try:
                self._post(hook, body)
                dispatched += 1
            except Exception as exc:
                logger.warning("webhook dispatch failed for %s event=%s: %s", hook.url, event, exc)
        return dispatched

    def _post(self, hook: Webhook, body: bytes) -> None:
        sig = ""
        if hook.secret:
            sig = hmac.new(hook.secret.encode(), body, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Aether-Webhook/1.0",
            "X-Aether-Event": "true",
        }
        if sig:
            headers["X-Aether-Signature"] = sig

        try:
            requests.post(hook.url, data=body, headers=headers, timeout=self.timeout)
        except NameError:
            # no requests; fallback urllib (stdlib)
            import urllib.request
            import urllib.error
            req = urllib.request.Request(hook.url, data=body, headers=headers, method="POST")
            try:
                urllib.request.urlopen(req, timeout=self.timeout)
            except urllib.error.URLError as e:
                raise e
