from django.urls import reverse

from .models import SiteSettings


def site_settings(request):
    return {
        "site_settings": SiteSettings.load()
    }


def admin_dashboard(request):
    """
    Dashboard statistics for the Django administration homepage.

    This only performs the database queries when the current
    request is inside Django admin and the user is authenticated.
    """

    context = {}

    if not request.path.startswith("/admin/"):
        return context

    if not request.user.is_authenticated:
        return context

    if not request.user.is_staff:
        return context

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
            consultation_date=__import__(
                "django.utils.timezone",
                fromlist=["localdate"],
            ).localdate()
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
            verification_status=(
                Caregiver.VerificationStatus.PENDING
            )
        ).count()
    )

    context["dashboard_caregivers_approved"] = (
        Caregiver.objects.filter(
            verification_status=(
                Caregiver.VerificationStatus.APPROVED
            )
        ).count()
    )

    context["dashboard_caregivers_active"] = (
        Caregiver.objects.filter(
            is_active=True
        ).count()
    )

    # ========================================================
    # ASSIGNMENTS
    # ========================================================

    context["dashboard_assignments_total"] = (
        CaregiverAssignment.objects.count()
    )

    context["dashboard_assignments_active"] = (
        CaregiverAssignment.objects.filter(
            status=CaregiverAssignment.Status.ASSIGNED
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
    # RECENT ITEMS
    # ========================================================

    context["dashboard_recent_homecare"] = (
        HomeCareRequest.objects.order_by("-created_at")[:5]
    )

    context["dashboard_recent_consultations"] = (
        Consultation.objects.order_by("-created_at")[:5]
    )

    context["dashboard_recent_payments"] = (
        Payment.objects.select_related(
            "quotation",
            "quotation__consultation",
            "quotation__homecare_request",
        ).order_by("-submitted_at")[:5]
    )

    context["dashboard_recent_caregivers"] = (
        Caregiver.objects.order_by("-created_at")[:5]
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