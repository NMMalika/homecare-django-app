from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import User

from .views import send_caregiver_assignment_email

from .models import (
    HomeCareRequest,
    HomeCareRequestAttachment,
    Referral,
    ReferralAttachment,
    Consultation,
    ConsultationAttachment,
    ConsultationSlot,
    Quotation,
    Payment,
    Caregiver,
    CaregiverAssignment,
    CaregiverCertificate,
    CaregiverDailyReport,
    CaregiverPayment,
)


# ============================================================
# HOME CARE REQUEST ATTACHMENT INLINE
# ============================================================

class HomeCareRequestAttachmentInline(admin.TabularInline):
    model = HomeCareRequestAttachment
    extra = 1


# ============================================================
# REFERRAL ATTACHMENT INLINE
# ============================================================

class ReferralAttachmentInline(admin.TabularInline):
    model = ReferralAttachment
    extra = 1


# ============================================================
# CONSULTATION ATTACHMENT INLINE
# ============================================================

class ConsultationAttachmentInline(admin.TabularInline):
    model = ConsultationAttachment
    extra = 1


# ============================================================
# CONSULTATION SLOT INLINE
# ============================================================

class ConsultationSlotInline(admin.TabularInline):
    model = ConsultationSlot
    extra = 1

    fields = (
        "date",
        "time",
        "duration_minutes",
        "is_available",
        "is_selected",
    )

    ordering = (
        "date",
        "time",
    )


# ============================================================
# HOME CARE REQUEST ADMIN
# ============================================================

@admin.register(HomeCareRequest)
class HomeCareRequestAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "full_name",
        "display_services",
        "phone",
        "preferred_date",
        "preferred_time",
        "status",
        "quotation_action",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
        "preferred_date",
    )

    search_fields = (
        "full_name",
        "phone",
        "email",
        "location",
    )

    filter_horizontal = (
        "services",
    )

    inlines = [
        HomeCareRequestAttachmentInline,
    ]

    @admin.display(description="Services Requested")
    def display_services(self, obj):

        services = obj.services.all()

        if services.exists():

            return ", ".join(
                [
                    getattr(
                        service,
                        "title",
                        getattr(
                            service,
                            "name",
                            str(service),
                        ),
                    )
                    for service in services
                ]
            )

        return "None"

    @admin.display(description="Quotation Action")
    def quotation_action(self, obj):

        if hasattr(obj, "quotation"):

            url = reverse(
                "admin:homecare_quotation_change",
                args=[obj.quotation.id],
            )

            return format_html(
                '<a class="button" href="{}">'
                "View Quotation"
                "</a>",
                url,
            )

        url = reverse(
            "homecare:create_quotation",
            args=[obj.id],
        )

        return format_html(
            '<a class="button" '
            'style="background-color:#28a745;'
            'color:white;" '
            'href="{}">'
            "Create Quotation"
            "</a>",
            url,
        )


# ============================================================
# REFERRAL ADMIN
# ============================================================

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "referrer_name",
        "referring_facility",
        "patient_name",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "referrer_name",
        "referrer_email",
        "patient_name",
        "patient_email",
        "referring_facility",
    )

    filter_horizontal = (
        "services_needed",
    )

    inlines = [
        ReferralAttachmentInline,
    ]


# ============================================================
# CONSULTATION SLOT ADMIN
# ============================================================

@admin.register(ConsultationSlot)
class ConsultationSlotAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "consultation",
        "patient_name",
        "date",
        "time",
        "duration_minutes",
        "availability_status",
        "selection_status",
    )

    list_filter = (
        "date",
        "is_available",
        "is_selected",
    )

    search_fields = (
        "consultation__first_name",
        "consultation__last_name",
        "consultation__email",
        "consultation__phone",
    )

    ordering = (
        "date",
        "time",
    )

    @admin.display(description="Patient")
    def patient_name(self, obj):

        return (
            f"{obj.consultation.first_name} "
            f"{obj.consultation.last_name}"
        )

    @admin.display(description="Availability")
    def availability_status(self, obj):

        if obj.is_available:

            return mark_safe(
                '<span style="'
                'background:#d1e7dd;'
                'color:#0f5132;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:600;">'
                "AVAILABLE"
                "</span>"
            )

        return mark_safe(
            '<span style="'
            'background:#f8d7da;'
            'color:#842029;'
            'padding:5px 9px;'
            'border-radius:5px;'
            'font-weight:600;">'
            "UNAVAILABLE"
            "</span>"
        )

    @admin.display(description="Selection")
    def selection_status(self, obj):

        if obj.is_selected:

            return mark_safe(
                '<span style="'
                'background:#198754;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "SELECTED"
                "</span>"
            )

        return "-"


# ============================================================
# CONSULTATION ADMIN
# ============================================================

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "patient_name",
        "email",
        "phone",
        "requested_date",
        "requested_time",
        "doctor_name",
        "status",
        "quotation_action",
        "next_step_action",
        "telemedicine_links",
        "created_at",
    )

    list_filter = (
        "status",
        "requested_date",
        "consultation_date",
        "created_at",
    )

    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "doctor__username",
        "doctor__first_name",
        "doctor__last_name",
        "doctor__email",
    )

    readonly_fields = (
        "patient_access_token",
        "doctor_access_token",
        "room_name",
        "patient_join_url",
        "doctor_join_url",
        "created_at",
        "updated_at",
    )

    inlines = [
        ConsultationAttachmentInline,
        ConsultationSlotInline,
    ]

    fieldsets = (
        (
            "Patient Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "services",
                    "message",
                )
            },
        ),
        (
            "Requested Appointment",
            {
                "fields": (
                    "requested_date",
                    "requested_time",
                )
            },
        ),
        (
            "Admin Review",
            {
                "fields": (
                    "doctor",
                    "status",
                    "admin_notes",
                )
            },
        ),
        (
            "Confirmed Appointment",
            {
                "fields": (
                    "consultation_date",
                    "consultation_time",
                    "duration_minutes",
                )
            },
        ),
        (
            "Telemedicine",
            {
                "fields": (
                    "room_name",
                    "patient_access_token",
                    "doctor_access_token",
                    "patient_join_url",
                    "doctor_join_url",
                )
            },
        ),
        (
            "Clinical Notes",
            {
                "fields": (
                    "doctor_notes",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(
        description="Patient",
        ordering="last_name",
    )
    def patient_name(self, obj):

        return (
            f"{obj.first_name} "
            f"{obj.last_name}"
        )

    @admin.display(description="Doctor")
    def doctor_name(self, obj):

        if not obj.doctor:
            return "Not Assigned"

        return (
            obj.doctor.get_full_name()
            or obj.doctor.username
        )

    @admin.display(description="Quotation")
    def quotation_action(self, obj):

        if hasattr(obj, "quotation"):

            url = reverse(
                "admin:homecare_quotation_change",
                args=[obj.quotation.id],
            )

            return format_html(
                '<a class="button" '
                'style="'
                'background:#0d6efd;'
                'color:white;'
                'padding:6px 10px;'
                'border-radius:5px;'
                'text-decoration:none;'
                'font-weight:600;" '
                'href="{}">'
                "VIEW QUOTE"
                "</a>",
                url,
            )

        url = reverse(
            "homecare:create_consultation_quotation",
            args=[obj.id],
        )

        return format_html(
            '<a class="button" '
            'style="'
            'background:#198754;'
            'color:white;'
            'padding:6px 10px;'
            'border-radius:5px;'
            'text-decoration:none;'
            'font-weight:700;" '
            'href="{}">'
            "CREATE QUOTATION"
            "</a>",
            url,
        )

    @admin.display(description="Next Step")
    def next_step_action(self, obj):

        if obj.status == Consultation.Status.PENDING:

            if not hasattr(obj, "quotation"):

                return mark_safe(
                    '<span style="'
                    'background:#ffc107;'
                    'color:#212529;'
                    'padding:5px 9px;'
                    'border-radius:5px;'
                    'font-weight:600;">'
                    "CREATE QUOTATION"
                    "</span>"
                )

            return mark_safe(
                '<span style="'
                'background:#6c757d;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:600;">'
                "REVIEW"
                "</span>"
            )

        if obj.status in (
            Consultation.Status.QUOTED,
            Consultation.Status.PAYMENT_PENDING,
        ):

            return mark_safe(
                '<span style="'
                'background:#fd7e14;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:600;">'
                "AWAITING PAYMENT"
                "</span>"
            )

        if obj.status == Consultation.Status.PAID:

            url = reverse(
                "homecare:schedule_consultation",
                args=[obj.id],
            )

            return format_html(
                '<a class="button" '
                'style="'
                'background:#0d6efd;'
                'color:white;'
                'padding:6px 10px;'
                'border-radius:5px;'
                'text-decoration:none;'
                'font-weight:700;" '
                'href="{}">'
                "ADD CONSULTATION SLOTS"
                "</a>",
                url,
            )

        if obj.status == Consultation.Status.SCHEDULED:

            return mark_safe(
                '<span style="'
                'background:#198754;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "READY FOR TELEMEDICINE"
                "</span>"
            )

        if obj.status == Consultation.Status.IN_PROGRESS:

            return mark_safe(
                '<span style="'
                'background:#0dcaf0;'
                'color:#212529;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "IN PROGRESS"
                "</span>"
            )

        if obj.status == Consultation.Status.COMPLETED:

            return mark_safe(
                '<span style="'
                'background:#198754;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "COMPLETED"
                "</span>"
            )

        if obj.status == Consultation.Status.CANCELLED:

            return mark_safe(
                '<span style="'
                'background:#dc3545;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "CANCELLED"
                "</span>"
            )

        return "-"

    @admin.display(description="Telemedicine")
    def telemedicine_links(self, obj):

        if obj.status != Consultation.Status.SCHEDULED:

            return mark_safe(
                '<span style="color:#6c757d;">'
                "Not scheduled"
                "</span>"
            )

        try:

            patient_url = reverse(
                "homecare:patient_telemedicine",
                kwargs={
                    "token": obj.patient_access_token
                },
            )

            doctor_url = reverse(
                "homecare:doctor_telemedicine",
                kwargs={
                    "token": obj.doctor_access_token
                },
            )

            return format_html(
                '<a href="{}" '
                'target="_blank" '
                'style="'
                'background:#198754;'
                'color:white;'
                'padding:5px 8px;'
                'border-radius:4px;'
                'text-decoration:none;'
                'font-weight:600;">'
                "PATIENT"
                "</a>"
                '&nbsp;'
                '<a href="{}" '
                'target="_blank" '
                'style="'
                'background:#0d6efd;'
                'color:white;'
                'padding:5px 8px;'
                'border-radius:4px;'
                'text-decoration:none;'
                'font-weight:600;">'
                "DOCTOR"
                "</a>",
                patient_url,
                doctor_url,
            )

        except Exception:

            return mark_safe(
                '<span style="color:#dc3545;">'
                "Telemedicine URL not configured"
                "</span>"
            )

    @admin.action(
        description="Mark selected appointments as completed"
    )
    def mark_completed(
        self,
        request,
        queryset,
    ):

        count = queryset.update(
            status=Consultation.Status.COMPLETED,
            updated_at=timezone.now(),
        )

        self.message_user(
            request,
            f"{count} appointment(s) marked completed.",
            messages.SUCCESS,
        )

    @admin.action(
        description="Cancel selected appointments"
    )
    def cancel_consultations(
        self,
        request,
        queryset,
    ):

        count = queryset.update(
            status=Consultation.Status.CANCELLED,
            updated_at=timezone.now(),
        )

        self.message_user(
            request,
            f"{count} appointment(s) cancelled.",
            messages.WARNING,
        )

    actions = (
        "mark_completed",
        "cancel_consultations",
    )


# ============================================================
# QUOTATION ADMIN
# ============================================================

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "quotation_client",
        "quotation_type",
        "amount",
        "payment_status",
        "sent_at",
        "payment_deadline",
        "created_at",
    )

    list_filter = (
        "payment_status",
        "created_at",
    )

    search_fields = (
        "homecare_request__full_name",
        "homecare_request__email",
        "homecare_request__phone",
        "consultation__first_name",
        "consultation__last_name",
        "consultation__email",
        "consultation__phone",
        "access_token",
    )

    fieldsets = (
        (
            "Quotation Source",
            {
                "fields": (
                    "homecare_request",
                    "consultation",
                )
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "base_amount",
                    "transportation_fee",
                    "discount_code",
                    "discount_amount",
                    "amount",
                    "description",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "payment_status",
                    "access_token",
                    "sent_at",
                    "payment_deadline",
                    "paid_at",
                    "reminder_sent_at",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = (
        "access_token",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Client")
    def quotation_client(self, obj):

        if obj.consultation:

            return (
                f"{obj.consultation.first_name} "
                f"{obj.consultation.last_name}"
            )

        if obj.homecare_request:

            return obj.homecare_request.full_name

        return "Unknown"

    @admin.display(description="Type")
    def quotation_type(self, obj):

        if obj.consultation:

            return mark_safe(
                '<strong style="color:#0d6efd;">'
                "APPOINTMENT"
                "</strong>"
            )

        if obj.homecare_request:

            return mark_safe(
                '<strong style="color:#198754;">'
                "HOME CARE"
                "</strong>"
            )

        return "Unknown"


# ============================================================
# PAYMENT ADMIN
# ============================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "get_client",
        "get_workflow",
        "get_quotation",
        "transaction_code",
        "amount_paid",
        "quotation_total",
        "amount_check",
        "status",
        "submitted_at",
        "verification_action",
    )

    list_filter = (
        "status",
        "payment_method",
        "submitted_at",
    )

    search_fields = (
        "payment_code",
        "quotation__homecare_request__full_name",
        "quotation__homecare_request__email",
        "quotation__homecare_request__phone",
        "quotation__consultation__first_name",
        "quotation__consultation__last_name",
        "quotation__consultation__email",
        "quotation__consultation__phone",
    )

    readonly_fields = (
        "submitted_at",
        "verified_at",
        "verified_by",
    )

    fieldsets = (
        (
            "Payment Information",
            {
                "fields": (
                    "quotation",
                    "payment_code",
                    "payment_method",
                    "amount",
                    "status",
                )
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "verified_at",
                    "verified_by",
                    "admin_notes",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "submitted_at",
                )
            },
        ),
    )

    @admin.display(description="Client")
    def get_client(self, obj):

        quotation = obj.quotation

        if quotation.consultation:

            return (
                f"{quotation.consultation.first_name} "
                f"{quotation.consultation.last_name}"
            )

        if quotation.homecare_request:

            return quotation.homecare_request.full_name

        return "Unknown"

    @admin.display(description="Workflow")
    def get_workflow(self, obj):

        quotation = obj.quotation

        if quotation.consultation:

            return mark_safe(
                '<span style="'
                'background:#0d6efd;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:600;">'
                "APPOINTMENT"
                "</span>"
            )

        if quotation.homecare_request:

            return mark_safe(
                '<span style="'
                'background:#198754;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:600;">'
                "HOME CARE"
                "</span>"
            )

        return "Unknown"

    @admin.display(description="Quotation")
    def get_quotation(self, obj):

        return f"Quotation #{obj.quotation.id}"

    @admin.display(description="Transaction Code")
    def transaction_code(self, obj):

        return format_html(
            '<strong style="'
            'color:#0d6efd;'
            'font-size:14px;">'
            '{}'
            '</strong>',
            obj.payment_code or "Not provided",
        )

    @admin.display(description="Amount Paid")
    def amount_paid(self, obj):

        amount = f"{obj.amount or 0:,.2f}"

        return format_html(
            '<strong style="'
            'color:#198754;'
            'font-size:14px;">'
            " N$ {}"
            "</strong>",
            amount,
        )

    @admin.display(description="Quotation Total")
    def quotation_total(self, obj):

        amount = f"{obj.quotation.amount or 0:,.2f}"

        return format_html(
            "<strong>"
            " N$ {}"
            "</strong>",
            amount,
        )

    @admin.display(description="Amount Check")
    def amount_check(self, obj):

        payment_amount = obj.amount or 0
        quotation_amount = obj.quotation.amount or 0

        if payment_amount == quotation_amount:

            return mark_safe(
                '<span style="'
                'display:inline-block;'
                'background:#d1e7dd;'
                'color:#0f5132;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:600;'
                'font-size:12px;">'
                "✓ AMOUNT MATCHES"
                "</span>"
            )

        return mark_safe(
            '<span style="'
            'display:inline-block;'
            'background:#f8d7da;'
            'color:#842029;'
            'padding:5px 9px;'
            'border-radius:5px;'
            'font-weight:600;'
            'font-size:12px;">'
            "⚠ AMOUNT MISMATCH"
            "</span>"
        )

    @admin.display(description="Action")
    def verification_action(self, obj):

        # ====================================================
        # PENDING PAYMENT
        # ====================================================

        if obj.status == Payment.Status.PENDING:

            url = reverse(
                "admin:homecare_payment_verify",
                args=[obj.id],
            )

            return format_html(
                '<div style="display:inline-flex; '
                'align-items:center; '
                'gap:6px; '
                'white-space:nowrap;">'
                '<a class="button" href="{}" '
                'style="background:#198754; '
                'color:#ffffff; '
                'font-weight:700; '
                'padding:6px 12px; '
                'border-radius:6px; '
                'text-decoration:none; '
                'font-size:11px; '
                'line-height:1.2; '
                'display:inline-flex; '
                'align-items:center;">'
                '✓ VERIFY'
                '</a>'
                '</div>',
                url,
            )

        # ====================================================
        # VERIFIED PAYMENT
        # ====================================================

        if obj.status == Payment.Status.VERIFIED:

            quotation = obj.quotation

            # ==================================================
            # CONSULTATION / APPOINTMENT PAYMENT
            # ==================================================

            if quotation.consultation:

                appointment_url = reverse(
                    "staff:appointments"
                )

                return format_html(
                    '<div style="display:inline-flex; '
                    'align-items:center; '
                    'gap:6px; '
                    'white-space:nowrap;">'

                    '<span style="'
                    'background:#198754; '
                    'color:#ffffff; '
                    'padding:6px 10px; '
                    'border-radius:6px; '
                    'font-weight:600; '
                    'font-size:11px; '
                    'line-height:1.2; '
                    'display:inline-block;">'
                    '✓ VERIFIED'
                    '</span>'

                    '<a class="button" href="{}" '
                    'style="'
                    'background:#0d6efd; '
                    'color:#ffffff; '
                    'padding:6px 10px; '
                    'border-radius:6px; '
                    'text-decoration:none; '
                    'font-weight:600; '
                    'font-size:11px; '
                    'line-height:1.2; '
                    'display:inline-flex; '
                    'align-items:center;">'
                    'VIEW APPOINTMENT'
                    '</a>'

                    '</div>',
                    appointment_url,
                )

            # ==================================================
            # HOME CARE PAYMENT
            # ==================================================

            if quotation.homecare_request:

                homecare_request = quotation.homecare_request

                # ------------------------------------------------
                # CAREGIVER ALREADY ASSIGNED
                # ------------------------------------------------

                if hasattr(
                    homecare_request,
                    "caregiver_assignment"
                ):

                    assignment = (
                        homecare_request.caregiver_assignment
                    )

                    assignment_url = reverse(
                        "staff:assignment_edit",
                        args=[assignment.id],
                    )

                    return format_html(
                        '<div style="display:inline-flex; '
                        'align-items:center; '
                        'gap:6px; '
                        'white-space:nowrap;">'

                        '<span style="'
                        'background:#198754; '
                        'color:#ffffff; '
                        'padding:6px 10px; '
                        'border-radius:6px; '
                        'font-weight:600; '
                        'font-size:11px; '
                        'line-height:1.2; '
                        'display:inline-block;">'
                        '✓ VERIFIED'
                        '</span>'

                        '<a class="button" href="{}" '
                        'style="'
                        'background:#0d6efd; '
                        'color:#ffffff; '
                        'padding:6px 10px; '
                        'border-radius:6px; '
                        'text-decoration:none; '
                        'font-weight:600; '
                        'font-size:11px; '
                        'line-height:1.2; '
                        'display:inline-flex; '
                        'align-items:center;">'
                        'CAREGIVER ASSIGNED'
                        '</a>'

                        '</div>',
                        assignment_url,
                    )

                # ------------------------------------------------
                # NO CAREGIVER ASSIGNED
                # ------------------------------------------------

                assignment_url = reverse(
                    "staff:caregiver_assignment_add"
                )

                assignment_url = (
                    f"{assignment_url}"
                    f"?homecare_request={homecare_request.id}"
                )

                return format_html(
                    '<div style="display:inline-flex; '
                    'align-items:center; '
                    'gap:6px; '
                    'white-space:nowrap;">'

                    '<span style="'
                    'background:#198754; '
                    'color:#ffffff; '
                    'padding:6px 10px; '
                    'border-radius:6px; '
                    'font-weight:600; '
                    'font-size:11px; '
                    'line-height:1.2; '
                    'display:inline-block;">'
                    '✓ VERIFIED'
                    '</span>'

                    '<a class="button" href="{}" '
                    'style="'
                    'background:#0d6efd; '
                    'color:#ffffff; '
                    'padding:6px 10px; '
                    'border-radius:6px; '
                    'text-decoration:none; '
                    'font-weight:600; '
                    'font-size:11px; '
                    'line-height:1.2; '
                    'display:inline-flex; '
                    'align-items:center;">'
                    'ASSIGN CAREGIVER'
                    '</a>'

                    '</div>',
                    assignment_url,
                )

        # ====================================================
        # REJECTED PAYMENT
        # ====================================================

        if obj.status == Payment.Status.REJECTED:

            return mark_safe(
                '<div style="display:inline-flex; '
                'align-items:center; '
                'gap:6px; '
                'white-space:nowrap;">'

                '<span style="'
                'background:#dc3545; '
                'color:#ffffff; '
                'padding:6px 10px; '
                'border-radius:6px; '
                'font-weight:600; '
                'font-size:11px; '
                'line-height:1.2; '
                'display:inline-block;">'
                '✕ REJECTED'
                '</span>'

                '</div>'
            )

        return "-"

    # ========================================================
    # PAYMENT CUSTOM URLS
    # ========================================================

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [
            path(
                "<int:payment_id>/verify/",
                self.admin_site.admin_view(
                    self.verify_payment_from_admin
                ),
                name="homecare_payment_verify",
            ),
        ]

        return custom_urls + urls

    # ========================================================
    # HELPER: DYNAMIC REDIRECT
    # ========================================================

    def get_redirect_url(self, request):
        next_url = request.POST.get("next") or request.GET.get("next")

        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url

        referer = request.META.get("HTTP_REFERER", "")

        if "/staff/" in referer:
            try:
                return reverse("staff:payments")
            except Exception:
                pass

        return reverse("admin:homecare_payment_changelist")

    # ========================================================
    # VERIFY PAYMENT
    # ========================================================

    def verify_payment_from_admin(
        self,
        request,
        payment_id,
    ):

        redirect_url = self.get_redirect_url(request)

        payment = (
            Payment.objects
            .select_related(
                "quotation",
                "quotation__homecare_request",
                "quotation__consultation",
            )
            .filter(id=payment_id)
            .first()
        )

        if not payment:

            messages.error(
                request,
                "Payment not found.",
            )

            return HttpResponseRedirect(redirect_url)

        if payment.status == Payment.Status.VERIFIED:

            messages.info(
                request,
                "This payment has already been verified.",
            )

            return HttpResponseRedirect(redirect_url)

        if payment.status == Payment.Status.REJECTED:

            messages.error(
                request,
                (
                    "A rejected payment cannot be verified. "
                    "Ask the client to submit a new payment."
                ),
            )

            return HttpResponseRedirect(redirect_url)

        quotation = payment.quotation

        homecare_request = quotation.homecare_request
        consultation = quotation.consultation

        if request.method == "GET":

            payment_amount = payment.amount or 0
            quotation_amount = quotation.amount or 0

            if consultation:

                client_name = (
                    f"{consultation.first_name} "
                    f"{consultation.last_name}"
                )

                workflow = "Book Appointment"

            elif homecare_request:

                client_name = homecare_request.full_name
                workflow = "Home Care"

            else:

                client_name = "Unknown Client"
                workflow = "Unknown"

            context = {
                **self.admin_site.each_context(request),

                "title": f"Verify Payment #{payment.id}",

                "payment": payment,
                "quotation": quotation,
                "homecare_request": homecare_request,
                "consultation": consultation,
                "client_name": client_name,
                "workflow": workflow,
                "redirect_url": redirect_url,

                "payment_amount": payment_amount,

                "quotation_amount": quotation_amount,

                "amount_matches": (
                    payment_amount
                    == quotation_amount
                ),

                "payment_method": (
                    payment.get_payment_method_display()
                ),

                "opts": self.model._meta,
            }

            return render(
                request,
                "admin/homecare/payment_verify.html",
                context,
            )

        if request.method != "POST":

            messages.error(
                request,
                "Invalid payment verification request.",
            )

            return HttpResponseRedirect(redirect_url)

        action = request.POST.get("action")
        now = timezone.now()

        # Handle REJECT Action
        if action == "reject":
            payment.status = Payment.Status.REJECTED
            payment.verified_by = request.user
            payment.verified_at = now
            payment.save(update_fields=["status", "verified_by", "verified_at"])

            messages.warning(
                request,
                f"Payment #{payment.id} has been rejected.",
            )
            return HttpResponseRedirect(redirect_url)

        # Handle VERIFY Action
        with transaction.atomic():

            payment.status = Payment.Status.VERIFIED
            payment.verified_at = now
            payment.verified_by = request.user

            payment.save(
                update_fields=[
                    "status",
                    "verified_at",
                    "verified_by",
                ]
            )

            quotation.payment_status = (
                Quotation.PaymentStatus.PAID
            )

            quotation.paid_at = now

            quotation.save(
                update_fields=[
                    "payment_status",
                    "paid_at",
                    "updated_at",
                ]
            )

            if consultation:

                consultation.status = (
                    Consultation.Status.PAID
                )

                consultation.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    (
                        f"Payment #{payment.id} verified. "
                        f"Appointment #{consultation.id} "
                        f"is now PAID."
                    ),
                )

            elif homecare_request:

                homecare_request.status = (
                    HomeCareRequest.Status.CONFIRMED
                )

                homecare_request.confirmed_at = now

                homecare_request.save(
                    update_fields=[
                        "status",
                        "confirmed_at",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    (
                        f"Payment #{payment.id} verified. "
                        f"Quotation #{quotation.id} is PAID "
                        f"and the home care request is CONFIRMED."
                    ),
                )

        return HttpResponseRedirect(redirect_url)

    # ========================================================
    # VERIFY PAYMENTS ACTION
    # ========================================================

    @admin.action(
        description="Verify selected payment(s)"
    )
    def verify_payments(
        self,
        request,
        queryset,
    ):

        verified_count = 0

        for payment in queryset:

            if payment.status != Payment.Status.PENDING:
                continue

            quotation = payment.quotation
            now = timezone.now()

            with transaction.atomic():

                payment.status = Payment.Status.VERIFIED
                payment.verified_at = now
                payment.verified_by = request.user

                payment.save(
                    update_fields=[
                        "status",
                        "verified_at",
                        "verified_by",
                    ]
                )

                quotation.payment_status = (
                    Quotation.PaymentStatus.PAID
                )

                quotation.paid_at = now

                quotation.save(
                    update_fields=[
                        "payment_status",
                        "paid_at",
                        "updated_at",
                    ]
                )

                if quotation.consultation:

                    consultation = quotation.consultation

                    consultation.status = (
                        Consultation.Status.PAID
                    )

                    consultation.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

                elif quotation.homecare_request:

                    homecare_request = (
                        quotation.homecare_request
                    )

                    homecare_request.status = (
                        HomeCareRequest.Status.CONFIRMED
                    )

                    homecare_request.confirmed_at = now

                    homecare_request.save(
                        update_fields=[
                            "status",
                            "confirmed_at",
                            "updated_at",
                        ]
                    )

                verified_count += 1

        self.message_user(
            request,
            (
                f"{verified_count} payment(s) "
                "verified successfully."
            ),
            messages.SUCCESS,
        )

    # ========================================================
    # REJECT PAYMENTS ACTION
    # ========================================================

    @admin.action(
        description="Reject selected payment(s)"
    )
    def reject_payments(
        self,
        request,
        queryset,
    ):

        rejected_count = 0

        for payment in queryset:

            if payment.status != Payment.Status.PENDING:
                continue

            payment.status = Payment.Status.REJECTED
            payment.verified_by = request.user
            payment.verified_at = timezone.now()

            payment.save(
                update_fields=[
                    "status",
                    "verified_by",
                    "verified_at",
                ]
            )

            rejected_count += 1

        self.message_user(
            request,
            (
                f"{rejected_count} payment(s) "
                f"rejected."
            ),
            messages.WARNING,
        )

    actions = [
        "verify_payments",
        "reject_payments",
    ]


    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

# ============================================================
# CAREGIVER CERTIFICATE INLINE
# ============================================================

class CaregiverCertificateInline(admin.TabularInline):

    model = CaregiverCertificate
    extra = 0

    fields = (
        "certificate_name",
        "certificate_number",
        "issuing_organization",
        "issue_date",
        "expiry_date",
        "document_link",
        "is_verified",
        "verification_notes",
    )

    readonly_fields = (
        "document_link",
    )

    @admin.display(description="Certificate Document")
    def document_link(self, obj):

        if not obj.document:

            return "No document uploaded"

        return format_html(
            '<a href="{}" target="_blank" '
            'style="'
            'background:#0d6efd;'
            'color:white;'
            'padding:5px 9px;'
            'border-radius:4px;'
            'text-decoration:none;'
            'font-weight:600;">'
            "VIEW CERTIFICATE"
            "</a>",
            obj.document.url,
        )


# ============================================================
# CAREGIVER ADMIN
# ============================================================

@admin.register(Caregiver)
class CaregiverAdmin(admin.ModelAdmin):

    list_display = (
        "display_name",
        "professional_title",
        "specialization",
        "phone",
        "email",
        "verification_status_display",
        "is_active",
        "verification_action",
    )

    list_filter = (
        "is_active",
        "verification_status",
    )

    search_fields = (
        "name",
        "professional_title",
        "specialization",
        "phone",
        "email",
        "user__first_name",
        "user__last_name",
        "user__username",
        "user__email",
    )

    ordering = (
        "name",
    )

    list_per_page = 25

    readonly_fields = (
        "approved_at",
        "approved_by",
        "created_at",
        "updated_at",
    )

    inlines = (
        CaregiverCertificateInline,
    )

    fieldsets = (

        # ----------------------------------------------------
        # PERSONAL INFORMATION
        # ----------------------------------------------------

        (
            "Personal Information",
            {
                "fields": (
                    "user",
                    "name",
                    "professional_title",
                    "specialization",
                    "phone",
                    "email",
                    "photo",
                )
            },
        ),

        # ----------------------------------------------------
        # AVAILABILITY
        # ----------------------------------------------------

        (
            "Availability",
            {
                "fields": (
                    "availability",
                    "is_active",
                )
            },
        ),

        # ----------------------------------------------------
        # DOCUMENTS
        # ----------------------------------------------------

        (
            "Professional Documents",
            {
                "fields": (
                    "cv",
                    "certificate_submitted",
                )
            },
        ),

        # ----------------------------------------------------
        # VERIFICATION
        # ----------------------------------------------------

        (
            "Verification",
            {
                "fields": (
                    "verification_status",
                    "verification_notes",
                    "approved_at",
                    "approved_by",
                )
            },
        ),

        # ----------------------------------------------------
        # SYSTEM
        # ----------------------------------------------------

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    # ========================================================
    # DISPLAY NAME
    # ========================================================

    @admin.display(
        description="Name",
        ordering="name",
    )
    def display_name(self, obj):

        if obj.name:

            return obj.name

        if obj.user:

            full_name = obj.user.get_full_name()

            if full_name:

                return full_name

            if obj.user.username:

                return obj.user.username

        return "Unnamed Caregiver"

    # ========================================================
    # VERIFICATION STATUS
    # ========================================================

    @admin.display(
        description="Verification Status"
    )
    def verification_status_display(self, obj):

        if (
            obj.verification_status
            == Caregiver.VerificationStatus.APPROVED
        ):

            return mark_safe(
                '<span style="'
                'background:#198754;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "APPROVED"
                "</span>"
            )

        if (
            obj.verification_status
            == Caregiver.VerificationStatus.REJECTED
        ):

            return mark_safe(
                '<span style="'
                'background:#dc3545;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "REJECTED"
                "</span>"
            )

        if (
            obj.verification_status
            == Caregiver.VerificationStatus.SUSPENDED
        ):

            return mark_safe(
                '<span style="'
                'background:#6c757d;'
                'color:white;'
                'padding:5px 9px;'
                'border-radius:5px;'
                'font-weight:700;">'
                "SUSPENDED"
                "</span>"
            )

        return mark_safe(
            '<span style="'
            'background:#ffc107;'
            'color:#212529;'
            'padding:5px 9px;'
            'border-radius:5px;'
            'font-weight:700;">'
            "PENDING VERIFICATION"
            "</span>"
        )

    # ========================================================
    # VERIFY BUTTON
    # ========================================================

    @admin.display(
        description="Verification"
    )
    def verification_action(self, obj):

        url = reverse(
            "admin:homecare_caregiver_verify",
            args=[obj.id],
        )

        if (
            obj.verification_status
            == Caregiver.VerificationStatus.APPROVED
        ):

            return format_html(
                '<a class="button" '
                'href="{}" '
                'style="'
                'background:#198754;'
                'color:white;'
                'padding:6px 12px;'
                'border-radius:5px;'
                'text-decoration:none;'
                'font-weight:700;">'
                "VIEW / UPDATE"
                "</a>",
                url,
            )

        return format_html(
            '<a class="button" '
            'href="{}" '
            'style="'
            'background:#0d6efd;'
            'color:white;'
            'padding:6px 12px;'
            'border-radius:5px;'
            'text-decoration:none;'
            'font-weight:700;">'
            "VERIFY"
            "</a>",
            url,
        )

    # ========================================================
    # CUSTOM ADMIN URLS
    # ========================================================

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [
            path(
                "<int:caregiver_id>/verify/",
                self.admin_site.admin_view(
                    self.verify_caregiver
                ),
                name="homecare_caregiver_verify",
            ),
        ]

        return custom_urls + urls

    # ========================================================
    # CAREGIVER VERIFICATION PAGE
    # ========================================================

    def verify_caregiver(
        self,
        request,
        caregiver_id,
    ):

        caregiver = (
            Caregiver.objects
            .select_related(
                "user",
                "approved_by",
            )
            .prefetch_related(
                "certificates",
            )
            .filter(
                id=caregiver_id
            )
            .first()
        )

        if not caregiver:

            messages.error(
                request,
                "Caregiver not found.",
            )

            return HttpResponseRedirect(
                reverse(
                    "admin:homecare_caregiver_changelist"
                )
            )

        # ====================================================
        # PROCESS APPROVAL / DECLINE
        # ====================================================

        if request.method == "POST":

            action = request.POST.get(
                "verification_action"
            )

            comment = request.POST.get(
                "verification_comment",
                "",
            ).strip()

            # ==================================================
            # APPROVE CAREGIVER
            # ==================================================

            if action == "approve":

                with transaction.atomic():

                    caregiver.verification_status = (
                        Caregiver.VerificationStatus.APPROVED
                    )

                    caregiver.verification_notes = comment

                    caregiver.approved_at = timezone.now()

                    caregiver.approved_by = request.user

                    caregiver.is_active = True

                    caregiver.save(
                        update_fields=[
                            "verification_status",
                            "verification_notes",
                            "approved_at",
                            "approved_by",
                            "is_active",
                            "updated_at",
                        ]
                    )

                    # ------------------------------------------
                    # ACTIVATE LINKED USER ACCOUNT
                    # ------------------------------------------

                    if caregiver.user:

                        user = caregiver.user

                        user.role = User.Role.CAREGIVER

                        user.is_active = True

                        # Caregivers do NOT receive Django admin access
                        user.is_staff = False

                        user.save(
                            update_fields=[
                                "role",
                                "is_active",
                                "is_staff",
                            ]
                        )

                messages.success(
                    request,
                    (
                        f"{caregiver.name or 'Caregiver'} "
                        "has been approved successfully. "
                        "The caregiver can now log in."
                    ),
                )

                return HttpResponseRedirect(
                    reverse(
                        "admin:homecare_caregiver_changelist"
                    )
                )

            # ==================================================
            # REJECT CAREGIVER
            # ==================================================

            if action == "reject":

                if not comment:

                    messages.error(
                        request,
                        (
                            "Please provide a comment "
                            "explaining why the caregiver "
                            "was declined."
                        ),
                    )

                else:

                    with transaction.atomic():

                        caregiver.verification_status = (
                            Caregiver.VerificationStatus.REJECTED
                        )

                        caregiver.verification_notes = comment

                        caregiver.approved_at = None

                        caregiver.approved_by = None

                        caregiver.is_active = False

                        caregiver.save(
                            update_fields=[
                                "verification_status",
                                "verification_notes",
                                "approved_at",
                                "approved_by",
                                "is_active",
                                "updated_at",
                            ]
                        )

                        # --------------------------------------
                        # DEACTIVATE LINKED USER ACCOUNT
                        # --------------------------------------

                        if caregiver.user:

                            user = caregiver.user

                            user.is_active = False

                            user.save(
                                update_fields=[
                                    "is_active",
                                ]
                            )

                    messages.warning(
                        request,
                        (
                            f"{caregiver.name or 'Caregiver'} "
                            "has been declined and their "
                            "login account has been deactivated."
                        ),
                    )

                    return HttpResponseRedirect(
                        reverse(
                            "admin:homecare_caregiver_changelist"
                        )
                    )

        # ====================================================
        # PAGE CONTEXT
        # ====================================================

        certificates = caregiver.certificates.all()

        context = {
            **self.admin_site.each_context(request),

            "title": (
                f"Verify Caregiver — "
                f"{caregiver.name or 'Unnamed Caregiver'}"
            ),

            "caregiver": caregiver,

            "certificates": certificates,

            "opts": self.model._meta,
        }

        return render(
            request,
            "admin/homecare/caregiver_verify.html",
            context,
        )


# ============================================================
# CAREGIVER ASSIGNMENT ADMIN
# ============================================================

@admin.register(CaregiverAssignment)
class CaregiverAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "homecare_request",
        "caregiver",
        "service_date",
        "service_time",
        "status",
        "assigned_by",
        "assigned_at",
    )

    list_filter = (
        "service_date",
        "status",
        "assigned_at",
        "caregiver",
    )

    search_fields = (
        "homecare_request__full_name",
        "homecare_request__phone",
        "homecare_request__email",
        "caregiver__name",
        "caregiver__phone",
    )

    readonly_fields = (
        "assigned_at",
        "assigned_by",
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):

        is_new_assignment = obj.pk is None

        if not obj.assigned_by:

            obj.assigned_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

        if (
            is_new_assignment
            and obj.caregiver
            and obj.caregiver.email
        ):

            transaction.on_commit(
                lambda: send_caregiver_assignment_email(
                    obj,
                    request.build_absolute_uri(
                        "/"
                    ).rstrip("/"),
                )
            )


# ============================================================
# CAREGIVER CERTIFICATE ADMIN
# ============================================================

@admin.register(CaregiverCertificate)
class CaregiverCertificateAdmin(admin.ModelAdmin):

    list_display = (
        "caregiver",
        "certificate_name",
        "certificate_number",
        "issuing_organization",
        "expiry_date",
        "is_verified",
        "uploaded_at",
    )

    list_filter = (
        "is_verified",
        "expiry_date",
    )

    search_fields = (
        "caregiver__name",
        "certificate_name",
        "certificate_number",
        "issuing_organization",
    )


# ============================================================
# CAREGIVER DAILY REPORT ADMIN
# ============================================================

@admin.register(CaregiverDailyReport)
class CaregiverDailyReportAdmin(admin.ModelAdmin):

    list_display = (
        "assignment",
        "report_date",
        "patient_condition",
        "next_visit_date",
        "submitted_at",
        "reviewed_by",
        "reviewed_at",
    )

    list_filter = (
        "patient_condition",
        "report_date",
        "reviewed_at",
    )

    search_fields = (
        "assignment__caregiver__name",
        "assignment__homecare_request__full_name",
        "care_provided",
        "patient_progress",
        "concerns",
    )

    readonly_fields = (
        "submitted_at",
        "updated_at",
    )


# ============================================================
# CAREGIVER PAYMENT ADMIN
# ============================================================

@admin.register(CaregiverPayment)
class CaregiverPaymentAdmin(admin.ModelAdmin):

    list_display = (
        "caregiver",
        "assignment",
        "amount",
        "status",
        "payment_reference",
        "payment_date",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_date",
        "created_at",
    )

    search_fields = (
        "caregiver__name",
        "assignment__homecare_request__full_name",
        "payment_reference",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )