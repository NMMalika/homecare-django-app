from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import Quotation, Referral


@receiver(post_save, sender=Quotation)
def send_referrer_thank_you(sender, instance, created, **kwargs):

    # ---------------------------------------------------------
    # Only process quotations that have been marked as PAID
    # ---------------------------------------------------------
    if instance.payment_status != Quotation.PaymentStatus.PAID:
        return

    # ---------------------------------------------------------
    # CONSULTATION QUOTATIONS
    #
    # A quotation can belong to either:
    #   1. HomeCareRequest
    #   2. Consultation
    #
    # Consultations do NOT have a referral_source.
    # Therefore, skip the referral thank-you process.
    # ---------------------------------------------------------
    homecare_request = getattr(
        instance,
        "homecare_request",
        None
    )

    if homecare_request is None:
        return

    # ---------------------------------------------------------
    # GET REFERRAL SOURCE
    # ---------------------------------------------------------
    referral = getattr(
        homecare_request,
        "referral_source",
        None
    )

    # No referral attached
    if referral is None:
        return

    # ---------------------------------------------------------
    # DO NOT SEND THE EMAIL TWICE
    # ---------------------------------------------------------
    if referral.thanked_at:
        return

    # ---------------------------------------------------------
    # SEND REFERRER THANK-YOU EMAIL
    # ---------------------------------------------------------
    subject = "Thank You for Your Referral - Hands-On Health"

    message = f"""
Dear {referral.referrer_name},

Thank you for referring {referral.patient_name} to Hands-On Health.

We are pleased to inform you that their home care service booking
has been confirmed and paid for.

Your trust in our care team allows us to deliver high-quality,
personalized healthcare to those in need.

If you know anyone else who needs skilled home nursing or care,
feel free to refer them to us at any time.

Warm regards,

Hands-On Health Team
Home-Based Healthcare Services
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[referral.referrer_email],
        fail_silently=False,
    )

    # ---------------------------------------------------------
    # MARK REFERRAL AS COMPLETED
    # ---------------------------------------------------------
    referral.status = Referral.Status.COMPLETED

    referral.thanked_at = timezone.localtime(
        timezone.now()
    )

    referral.save(
        update_fields=[
            "status",
            "thanked_at",
        ]
    )