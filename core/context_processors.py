from django.urls import reverse
from django.utils import timezone

from .models import SiteSettings


def site_settings(request):
    return {
        "site_settings": SiteSettings.load()
    }


def admin_dashboard(request):
    """
    Dashboard statistics for the Django administration homepage.

    ```
    Queries are only performed for authenticated staff users
    accessing the Django admin.
    """

    context = {}

    # ========================================================
    # ONLY RUN INSIDE DJANGO ADMIN
    # ========================================================

    if not request.path.startswith("/admin/"):
        return context

    if not request.user.is_authenticated:
        return context

    if not request.user.is_staff:
        return context

    # ========================================================
    # IMPORT MODELS
    # ========================================================

    from homecare.models import (
        HomeCareRequest,
        Consultation,
        Quotation,
        Payment,
        Caregiver,
        CaregiverAssignment,
        CaregiverDailyReport,
        CaregiverPayment,
        Referral,
    )

    # ========================================================
    # HOME CARE
    # ========================================================

    context["dashboard_homecare_total"] = (
        HomeCareRequest.objects.count()
    )

    context["dashboard_homecare_new"] = (
        HomeCareRequest.objects.filter(
            status=HomeCareRequest.Status.NEW
        ).count()
    )

    context["dashboard_homecare_confirmed"] = (
        HomeCareRequest.objects.filter(
            status=HomeCareRequest.Status.CONFIRMED
        ).count()
    )

    # HomeCareRequest DOES define ASSIGNED.
    context["dashboard_homecare_assigned"] = (
        HomeCareRequest.objects.filter(
            status=HomeCareRequest.Status.ASSIGNED
        ).count()
    )

    # ========================================================
    # CONSULTATIONS
    # ========================================================

    context["dashboard_consultations_total"] = (
        Consultation.objects.count()
    )

    context["dashboard_consultations_pending"] = (
        Consultation.objects.filter(
            status=Consultation.Status.PENDING
        ).count()
    )

    context["dashboard_consultations_paid"] = (
        Consultation.objects.filter(
            status=Consultation.Status.PAID
        ).count()
    )

    context["dashboard_consultations_scheduled"] = (
        Consultation.objects.filter(
            status=Consultation.Status.SCHEDULED
        ).count()
    )

    context["dashboard_consultations_today"] = (
        Consultation.objects.filter(
            consultation_date=timezone.localdate()
        ).count()
    )

    # ========================================================
    # QUOTATIONS
    # ========================================================

    context["dashboard_quotations_total"] = (
        Quotation.objects.count()
    )

    context["dashboard_quotations_pending"] = (
        Quotation.objects.filter(
            payment_status=Quotation.PaymentStatus.PENDING
        ).count()
    )

    context["dashboard_quotations_paid"] = (
        Quotation.objects.filter(
            payment_status=Quotation.PaymentStatus.PAID
        ).count()
    )

    # ========================================================
    # CLIENT PAYMENTS
    # ========================================================

    context["dashboard_payments_total"] = (
        Payment.objects.count()
    )

    context["dashboard_payments_pending"] = (
        Payment.objects.filter(
            status=Payment.Status.PENDING
        ).count()
    )

    context["dashboard_payments_verified"] = (
        Payment.objects.filter(
            status=Payment.Status.VERIFIED
        ).count()
    )

    context["dashboard_payments_rejected"] = (
        Payment.objects.filter(
            status=Payment.Status.REJECTED
        ).count()
    )

    # ========================================================
    # CAREGIVERS
    # ========================================================

    context["dashboard_caregivers_total"] = (
        Caregiver.objects.count()
    )

    context["dashboard_caregivers_pending"] = (
        Caregiver.objects.filter(
            verification_status=Caregiver.VerificationStatus.PENDING
        ).count()
    )

    context["dashboard_caregivers_approved"] = (
        Caregiver.objects.filter(
            verification_status=Caregiver.VerificationStatus.APPROVED
        ).count()
    )

    context["dashboard_caregivers_active"] = (
        Caregiver.objects.filter(
            is_active=True
        ).count()
    )

    # ========================================================
    # CAREGIVER ASSIGNMENTS
    # ========================================================

    context["dashboard_assignments_total"] = (
        CaregiverAssignment.objects.count()
    )

    # CaregiverAssignment.Status does NOT have ASSIGNED.
    #
    # An assignment is considered active when it has been
    # accepted or is currently in progress.
    context["dashboard_assignments_active"] = (
        CaregiverAssignment.objects.filter(
            status__in=[
                CaregiverAssignment.Status.ACCEPTED,
                CaregiverAssignment.Status.IN_PROGRESS,
            ]
        ).count()
    )

    context["dashboard_assignments_pending"] = (
        CaregiverAssignment.objects.filter(
            status=CaregiverAssignment.Status.PENDING
        ).count()
    )

    context["dashboard_assignments_completed"] = (
        CaregiverAssignment.objects.filter(
            status=CaregiverAssignment.Status.COMPLETED
        ).count()
    )

    context["dashboard_assignments_declined"] = (
        CaregiverAssignment.objects.filter(
            status=CaregiverAssignment.Status.DECLINED
        ).count()
    )

    # ========================================================
    # DAILY REPORTS
    # ========================================================

    context["dashboard_reports_total"] = (
        CaregiverDailyReport.objects.count()
    )

    context["dashboard_reports_unreviewed"] = (
        CaregiverDailyReport.objects.filter(
            reviewed_at__isnull=True
        ).count()
    )

    # ========================================================
    # CAREGIVER PAYMENTS
    # ========================================================

    context["dashboard_caregiver_payments_pending"] = (
        CaregiverPayment.objects.filter(
            status=CaregiverPayment.Status.PENDING
        ).count()
    )

    # ========================================================
    # REFERRALS
    # ========================================================

    context["dashboard_referrals_total"] = (
        Referral.objects.count()
    )

    context["dashboard_referrals_pending"] = (
        Referral.objects.filter(
            status=Referral.Status.PENDING
        ).count()
    )

    # ========================================================
    # RECENT HOME CARE REQUESTS
    # ========================================================

    context["dashboard_recent_homecare"] = (
        HomeCareRequest.objects.order_by(
            "-created_at"
        )[:5]
    )

    # ========================================================
    # RECENT CONSULTATIONS
    # ========================================================

    context["dashboard_recent_consultations"] = (
        Consultation.objects.order_by(
            "-created_at"
        )[:5]
    )

    # ========================================================
    # RECENT PAYMENTS
    # ========================================================

    context["dashboard_recent_payments"] = (
        Payment.objects.select_related(
            "quotation",
            "quotation__consultation",
            "quotation__homecare_request",
        ).order_by(
            "-submitted_at"
        )[:5]
    )

    # ========================================================
    # RECENT CAREGIVERS
    # ========================================================

    context["dashboard_recent_caregivers"] = (
        Caregiver.objects.order_by(
            "-created_at"
        )[:5]
    )

    # ========================================================
    # ADMIN URLS
    # ========================================================

    context["dashboard_urls"] = {
        "homecare": reverse(
            "admin:homecare_homecarerequest_changelist"
        ),

        "consultations": reverse(
            "admin:homecare_consultation_changelist"
        ),

        "quotations": reverse(
            "admin:homecare_quotation_changelist"
        ),

        "payments": reverse(
            "admin:homecare_payment_changelist"
        ),

        "caregivers": reverse(
            "admin:homecare_caregiver_changelist"
        ),

        "assignments": reverse(
            "admin:homecare_caregiverassignment_changelist"
        ),

        "reports": reverse(
            "admin:homecare_caregiverdailyreport_changelist"
        ),

        "caregiver_payments": reverse(
            "admin:homecare_caregiverpayment_changelist"
        ),

        "referrals": reverse(
            "admin:homecare_referral_changelist"
        ),

        "services": reverse(
            "admin:services_service_changelist"
        ),

        "service_categories": reverse(
            "admin:services_servicecategory_changelist"
        ),

        "users": reverse(
            "admin:accounts_user_changelist"
        ),
    }

    return context

