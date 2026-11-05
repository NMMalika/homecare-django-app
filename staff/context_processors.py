from django.apps import apps

from staff.models import FAQItem


def public_faqs(request):
    """
    Make active FAQs available to all Django templates.
    """
    return {
        "faqs": FAQItem.objects.filter(
            is_active=True
        ).order_by("display_order", "id")
    }


def _pending_count(app_label, model_name, statuses=None, null_field=None):
    """
    Count outstanding records using valid database status values.
    """
    model = apps.get_model(app_label, model_name)

    if null_field:
        return model.objects.filter(
            **{f"{null_field}__isnull": True}
        ).count()

    field = model._meta.get_field("status")

    if statuses is None:
        statuses = ["PENDING", "NEW"]

    valid_values = {
        str(value).upper(): value
        for value, label in field.flatchoices
    }

    selected = [
        valid_values[status.upper()]
        for status in statuses
        if status.upper() in valid_values
    ]

    if not selected:
        return 0

    return model.objects.filter(
        status__in=selected
    ).count()


def staff_notifications(request):
    """
    Provide global notification counts to the custom staff interface.

    Caregiver report notifications remain pending until the reports
    are reviewed and their reviewed_at fields are populated.
    """

    if not request.user.is_authenticated:
        return {}

    if getattr(request.user, "role", None) != "ADMIN":
        return {}

    counts = {
        "notify_caregivers": 0,
        "notify_homecare": 0,
        "notify_appointments": 0,
        "notify_referrals": 0,
        "notify_quotations": 0,
        "notify_payments": 0,
        "notify_assignments": 0,
        "notify_reports": 0,
        "notify_daily_reports": 0,
        "notify_weekly_reports": 0,
        "notify_caregiver_payments": 0,
        "notify_questions": 0,
        "notify_contacts": 0,
        "notify_chatbot": 0,
        "notify_testimonials": 0,
    }

    from homecare.models import (
        Caregiver,
        CaregiverAssignment,
        CaregiverDailyReport,
        CaregiverWeeklyReport,
        Quotation,
    )

    # Caregivers awaiting verification
    counts["notify_caregivers"] = Caregiver.objects.filter(
        verification_status="PENDING"
    ).count()

    # New home care requests
    counts["notify_homecare"] = _pending_count(
        "homecare",
        "HomeCareRequest",
        ["NEW"],
    )

    # Appointments awaiting attention
    counts["notify_appointments"] = _pending_count(
        "homecare",
        "Consultation",
        ["PENDING"],
    )

    # Referrals awaiting attention
    counts["notify_referrals"] = _pending_count(
        "homecare",
        "Referral",
        ["PENDING"],
    )

    # Quotations sent and awaiting payment
    counts["notify_quotations"] = Quotation.objects.filter(
        payment_status="PENDING",
        sent_at__isnull=False,
    ).count()

    # Payments awaiting verification
    counts["notify_payments"] = _pending_count(
        "homecare",
        "Payment",
        ["PENDING"],
    )

    # Assignments awaiting attention
    counts["notify_assignments"] = _pending_count(
        "homecare",
        "CaregiverAssignment",
        ["PENDING"],
    )

    # Daily caregiver reports not yet reviewed
    counts["notify_daily_reports"] = (
        CaregiverDailyReport.objects.filter(
            reviewed_at__isnull=True
        ).count()
    )

    # Weekly caregiver reports not yet reviewed
    counts["notify_weekly_reports"] = (
        CaregiverWeeklyReport.objects.filter(
            reviewed_at__isnull=True
        ).count()
    )

    # Combined report notification count
    counts["notify_reports"] = (
        counts["notify_daily_reports"]
        + counts["notify_weekly_reports"]
    )

    # Caregiver payments awaiting processing
    counts["notify_caregiver_payments"] = _pending_count(
        "homecare",
        "CaregiverPayment",
        ["PENDING"],
    )

    # Customer questions awaiting a reply
    from staff.models import CustomerQuestion

    counts["notify_questions"] = (
        CustomerQuestion.objects.filter(
            replied_at__isnull=True
        ).count()
    )

    # Contact enquiries awaiting resolution
    counts["notify_contacts"] = _pending_count(
        "staff",
        "ContactEnquiry",
        ["NEW", "PENDING"],
    )

    # Unanswered chatbot questions
    counts["notify_chatbot"] = _pending_count(
        "chatbot",
        "UnansweredQuestion",
        ["NEW", "PENDING", "UNANSWERED"],
    )

    # Testimonials awaiting moderation
    counts["notify_testimonials"] = _pending_count(
        "testimonials",
        "Testimonial",
        ["PENDING"],
    )

    # Total notifications, excluding the combined report count
    # to avoid counting daily/weekly reports twice.
    counts["notify_total"] = sum(
        value
        for key, value in counts.items()
        if key not in {
            "notify_reports",
            "notify_daily_reports",
            "notify_weekly_reports",
        }
    ) + counts["notify_reports"]

    return counts
