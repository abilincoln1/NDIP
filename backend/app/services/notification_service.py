"""
NDIP Phase D.3 — Notification Service (D3.7)
File: app/services/notification_service.py

Provider-abstracted notification delivery. Current provider: SMTP email.
Future provider slots: WhatsApp (Twilio/Meta API), SMS (Twilio), Push
(Firebase). Adding a new provider requires only:
  1. Implementing NotificationProvider protocol
  2. Adding the provider to PROVIDER_REGISTRY
  3. Setting the channel in the notification record

All notifications are logged to the `notifications` table before delivery.
If delivery fails, the record is updated with the error. Retry logic is
handled by the scheduler (D3.6 nightly job picks up pending/failed records).

SMTP configuration is read from environment variables — no credentials
appear in source code. In development (no SMTP config), notifications are
logged to stdout only.
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Protocol
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import utcnow

logger = logging.getLogger(__name__)


# ─── Provider Protocol ─────────────────────────────────────────────────────

class NotificationProvider(Protocol):
    """Any class implementing this protocol can be used as a notification
    provider. Returning a provider_ref string on success enables tracking."""

    def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        html_body: Optional[str] = None,
    ) -> str:
        """Send the notification. Returns a provider reference ID."""
        ...


# ─── SMTP Provider ─────────────────────────────────────────────────────────

class SmtpEmailProvider:
    """
    SMTP email provider. Reads configuration from environment:
      SMTP_HOST       — defaults to localhost
      SMTP_PORT       — defaults to 587
      SMTP_USER       — optional (skip auth if not set)
      SMTP_PASSWORD   — optional
      SMTP_FROM       — sender address (defaults to noreply@ndip.rtifn.org)
      SMTP_USE_TLS    — 'true' (default) or 'false'
    """

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "localhost")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.from_addr = os.getenv("SMTP_FROM", "noreply@ndip.rtifn.org")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        html_body: Optional[str] = None,
    ) -> str:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject or "NDIP Notification"
        msg["From"] = self.from_addr
        msg["To"] = recipient

        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.host, self.port)

            if self.user and self.password:
                server.login(self.user, self.password)

            server.sendmail(self.from_addr, [recipient], msg.as_string())
            server.quit()
            return f"smtp:{recipient}:{utcnow().isoformat()}"
        except Exception as e:
            raise RuntimeError(f"SMTP delivery failed: {e}") from e


class DevNullEmailProvider:
    """Development fallback — logs to stdout, never sends. Used when
    SMTP_HOST is not configured so the platform is runnable without
    an external mail server."""

    def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        html_body: Optional[str] = None,
    ) -> str:
        logger.info(
            "[DEV EMAIL] To: %s | Subject: %s\n%s",
            recipient, subject, body
        )
        return f"devnull:{recipient}:{utcnow().isoformat()}"


# ─── WhatsApp stub (future D4+) ────────────────────────────────────────────

class WhatsAppProvider:
    """Stub for future WhatsApp Business API integration (Twilio/Meta).
    Raises NotImplementedError until wired up in D4+."""

    def send(self, recipient, subject, body, html_body=None) -> str:
        raise NotImplementedError(
            "WhatsApp provider not yet configured. "
            "Set WHATSAPP_PROVIDER=twilio and configure TWILIO_* env vars."
        )


# ─── SMS stub (future D4+) ─────────────────────────────────────────────────

class SMSProvider:
    """Stub for future SMS integration."""

    def send(self, recipient, subject, body, html_body=None) -> str:
        raise NotImplementedError(
            "SMS provider not yet configured. "
            "Set SMS_PROVIDER=twilio and configure TWILIO_* env vars."
        )


# ─── Provider registry ─────────────────────────────────────────────────────

def _get_email_provider() -> NotificationProvider:
    if os.getenv("SMTP_HOST"):
        return SmtpEmailProvider()
    return DevNullEmailProvider()


PROVIDER_REGISTRY = {
    "email": _get_email_provider,
    "whatsapp": lambda: WhatsAppProvider(),
    "sms": lambda: SMSProvider(),
}


# ─── Message templates ─────────────────────────────────────────────────────

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

TEMPLATES = {
    "email_verification": {
        "subject": "Verify your NDIP email address",
        "body": (
            "Hello {full_name},\n\n"
            "Welcome to NDIP — the National & Diaspora Intelligence Platform.\n\n"
            "Please verify your email address by clicking the link below:\n\n"
            "{verification_url}\n\n"
            "This link expires in 24 hours.\n\n"
            "If you did not create an NDIP account, please ignore this email.\n\n"
            "RTIFN — National & Diaspora Intelligence Platform"
        ),
    },
    "password_reset": {
        "subject": "Reset your NDIP password",
        "body": (
            "Hello {full_name},\n\n"
            "A password reset was requested for your NDIP account.\n\n"
            "Click the link below to set a new password:\n\n"
            "{reset_url}\n\n"
            "This link expires in 30 minutes.\n\n"
            "If you did not request this, your account is safe — "
            "someone may have entered your email by mistake.\n\n"
            "RTIFN — National & Diaspora Intelligence Platform"
        ),
    },
    "welcome": {
        "subject": "Welcome to NDIP",
        "body": (
            "Hello {full_name},\n\n"
            "Your NDIP account has been created successfully.\n\n"
            "Your membership number is: {membership_number}\n\n"
            "To get started, please verify your email address and "
            "complete your member profile.\n\n"
            "Login at: {login_url}\n\n"
            "RTIFN — National & Diaspora Intelligence Platform"
        ),
    },
    "verification_approved": {
        "subject": "Your NDIP membership has been verified",
        "body": (
            "Hello {full_name},\n\n"
            "Your NDIP membership identity verification has been approved.\n\n"
            "You now have Verified Member status on the platform.\n\n"
            "RTIFN — National & Diaspora Intelligence Platform"
        ),
    },
    "verification_rejected": {
        "subject": "Your NDIP verification submission requires attention",
        "body": (
            "Hello {full_name},\n\n"
            "Your NDIP membership verification submission could not be approved "
            "at this time.\n\n"
            "Reason: {rejection_reason}\n\n"
            "Please log in and submit a new verification request with the "
            "required documents.\n\n"
            "Login at: {login_url}\n\n"
            "RTIFN — National & Diaspora Intelligence Platform"
        ),
    },
    "sponsorship_submitted": {
        "subject": "Ward sponsorship submitted for review",
        "body": (
            "Hello {full_name},\n\n"
            "Your ward sponsorship — {sponsorship_title} — has been submitted "
            "and is now under review.\n\n"
            "You will be notified when the review is complete.\n\n"
            "RTIFN — National & Diaspora Intelligence Platform"
        ),
    },
    "chapter_announcement": {
        "subject": "[NDIP] {chapter_name}: {announcement_title}",
        "body": (
            "Hello {full_name},\n\n"
            "A new announcement from your chapter ({chapter_name}):\n\n"
            "{announcement_body}\n\n"
            "Login to view more: {login_url}\n\n"
            "RTIFN — National & Diaspora Intelligence Platform"
        ),
    },
}


# ─── Notification Service ──────────────────────────────────────────────────

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def send(
        self,
        *,
        event_type: str,
        channel: str,
        recipient: str,
        member_id: Optional[UUID] = None,
        subject: Optional[str] = None,
        body: str,
        html_body: Optional[str] = None,
    ) -> UUID:
        """
        Persist a notification record then attempt delivery.
        Returns the notification UUID regardless of delivery outcome —
        failures are logged in the record for retry by the scheduler.
        """
        # Persist record first
        row = self.db.execute(text("""
            INSERT INTO notifications
                (member_id, event_type, channel, recipient, subject, body_preview, status)
            VALUES
                (CAST(:member_id AS UUID), :event_type, :channel, :recipient,
                 :subject, :body_preview, 'pending')
            RETURNING id
        """), {
            "member_id": str(member_id) if member_id else None,
            "event_type": event_type,
            "channel": channel,
            "recipient": recipient,
            "subject": subject,
            "body_preview": body[:500] if body else None,
        }).fetchone()
        notification_id = row.id
        self.db.commit()

        # Attempt delivery
        provider_factory = PROVIDER_REGISTRY.get(channel)
        if provider_factory is None:
            self._mark_failed(notification_id, f"Unknown channel: {channel}")
            return notification_id

        try:
            provider = provider_factory()
            provider_ref = provider.send(recipient, subject, body, html_body)
            self._mark_sent(notification_id, provider_ref)
        except NotImplementedError as e:
            # Future provider stub — mark as failed but don't raise
            self._mark_failed(notification_id, str(e))
        except Exception as e:
            logger.error("Notification delivery failed: %s", e)
            self._mark_failed(notification_id, str(e)[:500])

        return notification_id

    def send_from_template(
        self,
        *,
        template_name: str,
        channel: str,
        recipient: str,
        member_id: Optional[UUID] = None,
        context: dict,
    ) -> UUID:
        """Render a named template and send it."""
        template = TEMPLATES.get(template_name)
        if template is None:
            raise ValueError(f"Unknown notification template: {template_name}")

        subject = template["subject"].format(**context)
        body = template["body"].format(**context)

        return self.send(
            event_type=template_name,
            channel=channel,
            recipient=recipient,
            member_id=member_id,
            subject=subject,
            body=body,
        )

    # ─── Convenience senders ───────────────────────────────────────────────

    def send_email_verification(
        self, *, member_id: UUID, email: str, full_name: str, raw_token: str
    ) -> UUID:
        url = f"{FRONTEND_URL}/verify-email?member={member_id}&token={raw_token}"
        return self.send_from_template(
            template_name="email_verification",
            channel="email",
            recipient=email,
            member_id=member_id,
            context={"full_name": full_name, "verification_url": url},
        )

    def send_password_reset(
        self, *, member_id: UUID, email: str, full_name: str, raw_token: str
    ) -> UUID:
        url = f"{FRONTEND_URL}/reset-password?member={member_id}&token={raw_token}"
        return self.send_from_template(
            template_name="password_reset",
            channel="email",
            recipient=email,
            member_id=member_id,
            context={"full_name": full_name, "reset_url": url},
        )

    def send_welcome(
        self, *, member_id: UUID, email: str, full_name: str, membership_number: str
    ) -> UUID:
        return self.send_from_template(
            template_name="welcome",
            channel="email",
            recipient=email,
            member_id=member_id,
            context={
                "full_name": full_name,
                "membership_number": membership_number,
                "login_url": f"{FRONTEND_URL}/login",
            },
        )

    # ─── Internal helpers ──────────────────────────────────────────────────

    def _mark_sent(self, notification_id, provider_ref: str) -> None:
        self.db.execute(text("""
            UPDATE notifications
            SET status = 'sent', provider_ref = :ref, sent_at = now(), updated_at = now()
            WHERE id = CAST(:id AS UUID)
        """), {"ref": provider_ref[:255], "id": str(notification_id)})
        self.db.commit()

    def _mark_failed(self, notification_id, error: str) -> None:
        self.db.execute(text("""
            UPDATE notifications
            SET status = 'failed',
                error_message = :error,
                retry_count = retry_count + 1,
                updated_at = now()
            WHERE id = CAST(:id AS UUID)
        """), {"error": error, "id": str(notification_id)})
        self.db.commit()

    def retry_failed(self, max_retries: int = 3) -> dict:
        """Called by the hourly scheduler job. Retries failed notifications
        that haven't exceeded max_retries."""
        rows = self.db.execute(text("""
            SELECT id, channel, recipient, subject, body_preview
            FROM notifications
            WHERE status = 'failed'
              AND retry_count < :max_retries
            ORDER BY created_at
            LIMIT 50
        """), {"max_retries": max_retries}).fetchall()

        results = {"retried": 0, "succeeded": 0, "still_failed": 0}
        for row in rows:
            results["retried"] += 1
            provider_factory = PROVIDER_REGISTRY.get(row.channel)
            if provider_factory is None:
                results["still_failed"] += 1
                continue
            try:
                provider = provider_factory()
                ref = provider.send(row.recipient, row.subject, row.body_preview or "")
                self._mark_sent(row.id, ref)
                results["succeeded"] += 1
            except Exception:
                self._mark_failed(row.id, "Retry failed")
                results["still_failed"] += 1

        return results
