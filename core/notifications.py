
import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse

from core.models import SiteSettings

logger = logging.getLogger(__name__)


def get_staff_notification_emails():
    """
    Return all configured notification recipients.
    """

    site = SiteSettings.load()

    raw_emails = site.notification_emails or ""

    emails = [
        email.strip()
        for email in re.split(r"[,;\n]+", raw_emails)
        if email.strip()
    ]

    # Fall back to the main business email if no
    # notification recipients have been configured.
    if not emails and site.email:
        emails = [site.email.strip()]

    # Remove duplicates.
    return list(dict.fromkeys(emails))


def send_staff_notification(
    *,
    subject,
    message,
    url_name,
    object_id=None,
):
    """
    Send an email notification to all configured
    staff notification recipients.
    """

    site = SiteSettings.load()

    recipients = get_staff_notification_emails()

    if not recipients:
        logger.warning(
            "No staff notification recipients configured."
        )
        return False

    try:
        if object_id is not None:
            path = reverse(
                url_name,
                kwargs={"pk": object_id},
            )
        else:
            path = reverse(url_name)

        base_url = (
            (site.website or "").strip().rstrip("/")
            or getattr(settings, "SITE_URL", "").rstrip("/")
        )

        if not base_url:
            logger.warning(
                "No website URL configured for notifications."
            )
            return False

        dashboard_url = f"{base_url}{path}"

        email_body = f"""
Hello {site.business_name} Team,

{message}

----------------------------------------

OPEN STAFF DASHBOARD

{dashboard_url}

----------------------------------------

Please log in to review this notification.

This is an automated message from
{site.business_name}.
"""

        def deliver():
            for recipient in recipients:
                try:
                    send_mail(
                        subject=f"{site.business_name} | {subject}",
                        message=email_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient],
                        fail_silently=False,
                    )
                except Exception:
                    logger.exception(
                        "Notification delivery failed for %s",
                        recipient,
                    )

        transaction.on_commit(deliver)

        return True

    except Exception:
        logger.exception(
            "Failed to prepare staff notification."
        )
        return False
