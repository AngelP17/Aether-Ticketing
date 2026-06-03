"""
Email Service (Phase 8): outbound notifications + inbound ticket stub.

Config-driven (SMTP_* from settings). No creds in code. Real sends only when configured.
Outbound: on decision/recompute, recommendation apply, SLA risk, comment, assignment.
Inbound: simple parser stub (subject key match or new ticket from email body).
Uses stdlib smtplib + email for minimal deps.
"""
from __future__ import annotations

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Optional

from apps.api.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM
        self.use_tls = settings.SMTP_USE_TLS

    @property
    def is_configured(self) -> bool:
        return bool(self.host)

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send a plain (or html) email. Returns success. No-op + log if not configured."""
        if not self.is_configured:
            logger.info("[email] not configured; would send to=%s subject=%s", to, subject)
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.host or "localhost", self.port or 25) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_addr, [to], msg.as_string())
            logger.info("[email] sent to=%s subject=%s", to, subject)
            return True
        except Exception as exc:
            logger.exception("[email] send failed: %s", exc)
            return False

    def send_decision_notification(self, ticket_id: str, to: str, priority: float, band: str, root_cause: str) -> bool:
        subject = f"[Aether] Decision for {ticket_id}: {band} (score {priority})"
        body = f"""Ticket {ticket_id} has a new decision.
Priority: {priority}
Band: {band}
Root cause: {root_cause}

Review in Command Center or replay the ticket.
"""
        return self.send_email(to, subject, body)

    def send_action_applied(self, ticket_id: str, to: str, action: str) -> bool:
        subject = f"[Aether] Action applied to {ticket_id}: {action}"
        body = f"Action '{action}' was applied to ticket {ticket_id} (audit logged).\nCheck replay for details."
        return self.send_email(to, subject, body)

    # Inbound stub (called from future ingest or route)
    def parse_inbound_to_ticket(self, raw_email: str) -> dict[str, Any]:
        """Very basic parser stub. In real: use email lib + header parse for requester, subject->title, body->desc, look for [IT-xxx] key to update."""
        # Placeholder: extract first lines
        lines = [line.strip() for line in raw_email.splitlines() if line.strip()]
        title = lines[0][:200] if lines else "Inbound email ticket"
        desc = "\n".join(lines[1:10])
        return {
            "title": title,
            "description": desc or "Parsed from inbound email (stub).",
            "requester": "email-inbound@stub.local",
            "priority": "Medium",
            # In real: parse for existing ticket key in subject, call update instead of create
        }
