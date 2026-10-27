from functools import wraps
import logging
import secrets
from datetime import timedelta
from django.conf import settings as django_settings
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods


from accounts.models import User

from services.models import (
    Service,
    ServiceCategory,
)

from staff.forms import (
    ServiceForm,
    CaregiverAssignmentForm,
    CaregiverDailyReportForm,
    CaregiverPaymentForm,
)

from core.forms import SiteSettingsForm
from core.models import SiteSettings

from homecare.forms import (
    HomeCareRequestForm,
)

from homecare.models import (
    Caregiver,
    CaregiverAssignment,
    CaregiverCertificate,
    CaregiverDailyReport,
    CaregiverPayment,
    CaregiverInvitation,
    HomeCareRequest,
    Consultation,
    Payment,
    Quotation,
    Referral,
)

from homecare.views import (
    verify_payment as homecare_verify_payment,
    send_caregiver_assignment_email,
    create_consultation_quotation as homecare_create_consultation_quotation,
)
from .models import FAQItem, QuestionFormSettings, CustomerQuestion
from .forms import StaffCaregiverInviteForm
from staff.models import ContactEnquiry
from testimonials.models import Testimonial
from leadership.models import Founder
from leadership.forms import FounderForm
from hero.models import HeroSlide
from hero.forms import HeroSlideForm

logger = logging.getLogger(__name__)
# ============================================================
# ADMIN ACCESS
# ============================================================


def admin_required(view_func):
    """
    Only Hands-On Health ADMIN users can access
    the custom staff dashboard.
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if request.user.role != User.Role.ADMIN:
            raise PermissionDenied(
                "Only Hands-On Health administrators can access this dashboard."
            )

        return view_func(request, *args, **kwargs)

    return wrapper


@admin_required
def consultation_quotation(request, consultation_id):
    return homecare_create_consultation_quotation(
        request,
        consultation_id=consultation_id,
    )


# ============================================================
# CAREGIVER REGISTRATION INVITATION HELPER
# ============================================================


def send_caregiver_registration_invitation(request, caregiver):
    """
    Create or reuse a valid invitation and email the caregiver
    a secure registration link.
    """

    email = (
        (
            getattr(caregiver, "email", None)
            or getattr(getattr(caregiver, "user", None), "email", None)
            or ""
        )
        .strip()
        .lower()
    )

    if not email:
        raise ValueError("The caregiver does not have an email address.")

    user = caregiver.user

    if user is None:
        raise ValueError(
            "This caregiver has no linked user account. "
            "Create the caregiver account before sending an invitation."
        )

    if user.has_usable_password():
        return False

    now = timezone.now()

    # Reuse an existing valid invitation to avoid sending
    # multiple different links unnecessarily.
    invitation = (
        CaregiverInvitation.objects.filter(
            caregiver=caregiver,
            used_at__isnull=True,
            expires_at__gt=now,
        )
        .order_by("-expires_at")
        .first()
    )

    if invitation is None:
        # Invalidate expired or superseded invitations.
        CaregiverInvitation.objects.filter(
            caregiver=caregiver,
            used_at__isnull=True,
        ).update(used_at=now)

        invitation = CaregiverInvitation.objects.create(
            caregiver=caregiver,
            email=email,
            token=secrets.token_urlsafe(48),
            expires_at=now + timedelta(days=3),
            created_by=request.user,
        )

    registration_url = request.build_absolute_uri(
        reverse(
            "caregivers:register_invitation",
            kwargs={"token": invitation.token},
        )
    )

    send_mail(
        subject="Complete Your Hands-On Health Caregiver Registration",
        message=f"""
Hello {caregiver.name},

You have been invited to join Hands-On Health as a caregiver.

Complete your registration using this secure link:

{registration_url}

This invitation expires in 3 days.

Your account will remain inactive until an administrator
reviews and approves your caregiver profile.

Kind regards,
Hands-On Health
""",
        from_email=getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            None,
        ),
        recipient_list=[email],
        fail_silently=False,
    )

    return True


# ============================================================
# STAFF LOGIN
# ============================================================


def staff_login(request):

    site_settings = SiteSettings.load()

    if request.user.is_authenticated:

        if request.user.role == User.Role.ADMIN:
            return redirect("staff:dashboard")

        logout(request)

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:

            if user.role != User.Role.ADMIN:

                messages.error(
                    request,
                    "You do not have permission to access the staff dashboard.",
                )

                return render(
                    request,
                    "staff/login.html",
                    {
                        "site_settings": site_settings,
                    },
                )

            login(
                request,
                user,
            )

            next_url = request.POST.get("next") or request.GET.get("next")

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect("staff:dashboard")

        messages.error(
            request,
            "Invalid username or password.",
        )

    return render(
        request,
        "staff/login.html",
        {
            "site_settings": site_settings,
        },
    )


# ============================================================
# STAFF LOGOUT
# ============================================================


@login_required
def staff_logout(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully.",
    )

    return redirect("staff:login")


# ============================================================
# CHANGE PASSWORD
# ============================================================


@admin_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST,
        )

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(
                request,
                user,
            )

            messages.success(
                request,
                "Your password has been changed successfully.",
            )

            return redirect("staff:dashboard")

    else:

        form = PasswordChangeForm(
            request.user,
        )

    return render(
        request,
        "staff/change_password.html",
        {
            "form": form,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# STAFF DASHBOARD
# ============================================================


@admin_required
def dashboard(request):

    pending_caregivers = Caregiver.objects.filter(
        verification_status=Caregiver.VerificationStatus.PENDING
    ).count()

    recent_requests = HomeCareRequest.objects.order_by("-created_at")[:5]
    recent_referrals = (
        Referral.objects.select_related("homecare_request")
        .prefetch_related("services_needed")
        .order_by("-created_at")[:5]
    )

    recent_appointments = Consultation.objects.select_related("doctor").order_by(
        "-created_at"
    )[:5]

    recent_payments = Payment.objects.select_related(
        "quotation",
        "quotation__homecare_request",
        "quotation__consultation",
        "verified_by",
    ).order_by("-submitted_at")[:5]

    recent_quotations = Quotation.objects.select_related(
        "homecare_request",
        "consultation",
    ).order_by("-created_at")[:5]

    recent_assignments = CaregiverAssignment.objects.select_related(
        "caregiver",
        "homecare_request",
        "assigned_by",
    ).order_by("-assigned_at")[:5]

    context = {
        "site_settings": SiteSettings.load(),
        "pending_caregivers": pending_caregivers,
        "caregiver_count": (Caregiver.objects.count()),
        "assignment_count": (CaregiverAssignment.objects.count()),
        "homecare_request_count": (HomeCareRequest.objects.count()),
        "appointment_count": (Consultation.objects.count()),
        "payment_count": (Payment.objects.count()),
        "quotation_count": (Quotation.objects.count()),
        "report_count": (CaregiverDailyReport.objects.count()),
        "caregiver_payment_count": (CaregiverPayment.objects.count()),
        "recent_requests": recent_requests,
        "recent_appointments": recent_appointments,
        "recent_payments": recent_payments,
        "recent_quotations": recent_quotations,
        "recent_assignments": recent_assignments,
        "referral_count": Referral.objects.count(),
        "pending_referrals": Referral.objects.filter(status="PENDING").count(),
        "recent_referrals": recent_referrals,
    }

    return render(
        request,
        "staff/dashboard.html",
        context,
    )


# ============================================================
# CAREGIVER DIRECTORY AND AUTOMATIC REGISTRATION STATUS
# ============================================================


@admin_required
def caregivers(request):
    current_status = request.GET.get("status", "").strip()
    search = request.GET.get("q", "").strip()

    caregivers_queryset = (
        Caregiver.objects.select_related("user", "approved_by")
        .prefetch_related("certificates")
        .order_by("name")
    )

    # Filter by the caregiver's actual verification status.
    valid_statuses = {value for value, label in Caregiver.VerificationStatus.choices}

    if current_status in valid_statuses:
        caregivers_queryset = caregivers_queryset.filter(
            verification_status=current_status
        )
    else:
        current_status = ""

    # Search caregivers.
    if search:
        caregivers_queryset = caregivers_queryset.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
        )

    now = timezone.now()

    # Automatically determine the status displayed in the directory.
    for caregiver in caregivers_queryset:
        user = caregiver.user

        # A usable password indicates that registration was completed.
        caregiver.registration_complete = bool(user and user.has_usable_password())

        caregiver.latest_invitation = (
            CaregiverInvitation.objects.filter(caregiver=caregiver)
            .order_by("-created_at")
            .first()
        )

        invitation = caregiver.latest_invitation

        caregiver.invitation_is_valid = bool(
            invitation and invitation.used_at is None and invitation.expires_at > now
        )

        caregiver.invitation_expired = bool(
            invitation and invitation.used_at is None and invitation.expires_at <= now
        )

        # Determine the label to display in the staff directory.
        if caregiver.verification_status == Caregiver.VerificationStatus.APPROVED:
            caregiver.workflow_status = "approved"

        elif caregiver.verification_status == Caregiver.VerificationStatus.REJECTED:
            caregiver.workflow_status = "rejected"

        elif caregiver.registration_complete:
            # Registration submitted: ready for staff verification.
            caregiver.workflow_status = "verify"

        elif caregiver.invitation_is_valid:
            caregiver.workflow_status = "invitation_sent"

        elif caregiver.invitation_expired:
            caregiver.workflow_status = "invitation_expired"

        else:
            caregiver.workflow_status = "invitation_needed"

        # Only show the resend option if registration is incomplete
        # and there is no currently valid invitation.
        caregiver.can_resend_invitation = bool(
            caregiver.verification_status == Caregiver.VerificationStatus.PENDING
            and not caregiver.registration_complete
            and not caregiver.invitation_is_valid
        )

    pending_caregivers = Caregiver.objects.filter(
        verification_status=Caregiver.VerificationStatus.PENDING
    ).count()

    return render(
        request,
        "staff/caregivers.html",
        {
            "caregivers": caregivers_queryset,
            "current_status": current_status,
            "verification_choices": (Caregiver.VerificationStatus.choices),
            "pending_caregivers": pending_caregivers,
            "search": search,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# CAREGIVER VERIFICATION AND ACTIVATION EMAIL
# ============================================================


@admin_required
@require_http_methods(["GET", "POST"])
def caregiver_verify(request, pk):

    caregiver = get_object_or_404(
        Caregiver.objects.select_related(
            "user",
            "approved_by",
        ).prefetch_related("certificates"),
        pk=pk,
    )

    if request.method == "POST":

        action = request.POST.get("action", "").strip().lower()
        comment = request.POST.get("comment", "").strip()

        # ----------------------------------------------------
        # APPROVE CAREGIVER
        # ----------------------------------------------------

        if action == "approve":

            # Do not approve a caregiver who has not completed
            # the invitation registration process.
            if not caregiver.user or not caregiver.user.has_usable_password():
                messages.error(
                    request,
                    (
                        "This caregiver has not completed registration. "
                        "They must submit their registration form before "
                        "you can verify and approve the application."
                    ),
                )
                return redirect("staff:caregivers")

            with transaction.atomic():

                caregiver.verification_status = Caregiver.VerificationStatus.APPROVED
                caregiver.is_active = True
                caregiver.verification_notes = comment
                caregiver.approved_by = request.user
                caregiver.approved_at = timezone.now()
                caregiver.save()

                if caregiver.user:
                    caregiver.user.is_active = True
                    caregiver.user.save(update_fields=["is_active"])

            recipient_email = (
                getattr(caregiver.user, "email", None)
                or getattr(caregiver, "email", None)
                or ""
            ).strip()

            if recipient_email:

                try:
                    login_url = request.build_absolute_uri(reverse("caregivers:login"))

                    send_mail(
                        subject=(
                            "Your Hands-On Health Caregiver "
                            "Account Has Been Approved"
                        ),
                        message=f"""
Hello {caregiver.name},

Your caregiver registration with Hands-On Health has been
reviewed and approved.

Your caregiver account is now active. You can sign in using
the email address you registered with and the password you
created during registration.

Caregiver login:
{login_url}

If you have trouble accessing your account, please contact
Hands-On Health.

Kind regards,
Hands-On Health
""",
                        from_email=getattr(
                            settings,
                            "DEFAULT_FROM_EMAIL",
                            None,
                        ),
                        recipient_list=[recipient_email],
                        fail_silently=False,
                    )

                    messages.success(
                        request,
                        (
                            f"{caregiver.name} has been approved "
                            "and activated. An activation email "
                            f"was sent to {recipient_email}."
                        ),
                    )

                except Exception as email_error:
                    messages.warning(
                        request,
                        (
                            f"{caregiver.name} has been approved "
                            "and activated, but the activation email "
                            f"could not be sent: {email_error}"
                        ),
                    )

            else:
                messages.warning(
                    request,
                    (
                        f"{caregiver.name} has been approved, "
                        "but no email address was found."
                    ),
                )

            return redirect("staff:caregivers")

            # ----------------------------------------------------
        # SUSPEND APPROVED CAREGIVER
        # ----------------------------------------------------

        elif action == "suspend":

            if caregiver.verification_status != Caregiver.VerificationStatus.APPROVED:
                messages.error(request, "Only approved caregivers can be suspended.")
                return redirect("staff:caregivers")

            if not comment:
                messages.error(
                    request, "Please provide a reason for suspending this caregiver."
                )
                return redirect("staff:caregiver_verify", pk=caregiver.pk)

            with transaction.atomic():

                caregiver.verification_status = Caregiver.VerificationStatus.SUSPENDED
                caregiver.is_active = False
                caregiver.verification_notes = comment
                caregiver.save()

                if caregiver.user:
                    caregiver.user.is_active = False
                    caregiver.user.save(update_fields=["is_active"])

            recipient_email = (
                getattr(caregiver.user, "email", None)
                or getattr(caregiver, "email", None)
                or ""
            ).strip()

            if recipient_email:
                try:
                    send_mail(
                        subject="Hands-On Health Caregiver Account Suspended",
                        message=(
                            f"Hello {caregiver.name},\n\n"
                            "Your Hands-On Health caregiver account has "
                            "been temporarily suspended.\n\n"
                            f"Reason: {comment}\n\n"
                            "You will not be able to access your caregiver "
                            "account until an administrator reactivates it.\n\n"
                            "Please contact Hands-On Health for assistance.\n\n"
                            "Kind regards,\nHands-On Health"
                        ),
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        recipient_list=[recipient_email],
                        fail_silently=False,
                    )
                except Exception as error:
                    messages.warning(
                        request, f"Caregiver suspended, but email failed: {error}"
                    )

            messages.success(
                request, f"{caregiver.name} has been suspended successfully."
            )

            return redirect("staff:caregivers")

        # ----------------------------------------------------
        # REACTIVATE SUSPENDED CAREGIVER
        # ----------------------------------------------------

        elif action == "reactivate":

            if caregiver.verification_status != Caregiver.VerificationStatus.SUSPENDED:
                messages.error(request, "Only suspended caregivers can be reactivated.")
                return redirect("staff:caregivers")

            if not caregiver.user or not caregiver.user.has_usable_password():
                messages.error(
                    request,
                    "This caregiver must have a completed registration before reactivation.",
                )
                return redirect("staff:caregivers")

            with transaction.atomic():

                caregiver.verification_status = Caregiver.VerificationStatus.APPROVED
                caregiver.is_active = True
                caregiver.verification_notes = comment
                caregiver.save()

                caregiver.user.is_active = True
                caregiver.user.save(update_fields=["is_active"])

            recipient_email = (caregiver.user.email or caregiver.email or "").strip()

            if recipient_email:
                try:
                    login_url = request.build_absolute_uri(reverse("caregivers:login"))

                    send_mail(
                        subject="Your Hands-On Health Caregiver Account Has Been Reactivated",
                        message=(
                            f"Hello {caregiver.name},\n\n"
                            "Your Hands-On Health caregiver account has "
                            "been reactivated.\n\n"
                            "You can now log in using your existing credentials.\n\n"
                            f"Login: {login_url}\n\n"
                            "Kind regards,\nHands-On Health"
                        ),
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        recipient_list=[recipient_email],
                        fail_silently=False,
                    )
                except Exception as error:
                    messages.warning(
                        request, f"Caregiver reactivated, but email failed: {error}"
                    )

            messages.success(
                request, f"{caregiver.name} has been reactivated successfully."
            )

            return redirect("staff:caregivers")

        # ----------------------------------------------------
        # DECLINE CAREGIVER
        # ----------------------------------------------------

        elif action == "decline":

            with transaction.atomic():

                caregiver.verification_status = Caregiver.VerificationStatus.REJECTED
                caregiver.is_active = False
                caregiver.verification_notes = comment
                caregiver.save()

                if caregiver.user:
                    caregiver.user.is_active = False
                    caregiver.user.save(update_fields=["is_active"])

            recipient_email = (
                getattr(caregiver.user, "email", None)
                or getattr(caregiver, "email", None)
                or ""
            ).strip()

            if recipient_email:
                try:
                    send_mail(
                        subject=(
                            "Update on Your Hands-On Health " "Caregiver Application"
                        ),
                        message=f"""
Hello {caregiver.name},

Your caregiver application with Hands-On Health has not
been approved at this time.

If you need clarification or would like to discuss your
application, please contact Hands-On Health.

Kind regards,
Hands-On Health
""",
                        from_email=getattr(
                            settings,
                            "DEFAULT_FROM_EMAIL",
                            None,
                        ),
                        recipient_list=[recipient_email],
                        fail_silently=False,
                    )
                except Exception:
                    # The decision remains saved even if email fails.
                    pass

            messages.warning(
                request,
                f"{caregiver.name} has been declined.",
            )

            return redirect("staff:caregivers")

        else:
            messages.error(
                request,
                "Please select a valid verification action.",
            )

    return render(
        request,
        "staff/caregiver_verify.html",
        {
            "caregiver": caregiver,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# CAREGIVER ASSIGNMENTS
# ============================================================


@admin_required
def caregiver_assignments(request):

    current_status = request.GET.get(
        "status",
        "",
    )

    search = request.GET.get(
        "q",
        "",
    ).strip()

    assignments_queryset = (
        CaregiverAssignment.objects.select_related(
            "caregiver",
            "homecare_request",
            "assigned_by",
        )
        .prefetch_related(
            "homecare_request__services",
        )
        .order_by(
            "-assigned_at",
        )
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:

        assignments_queryset = assignments_queryset.filter(
            Q(caregiver__name__icontains=search)
            | Q(caregiver__user__first_name__icontains=search)
            | Q(caregiver__user__last_name__icontains=search)
            | Q(caregiver__user__email__icontains=search)
        )

    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    if current_status:

        assignments_queryset = assignments_queryset.filter(status=current_status)

    return render(
        request,
        "staff/assignments.html",
        {
            "assignments": assignments_queryset,
            "current_status": current_status,
            "search": search,
            "status_choices": (CaregiverAssignment.Status.choices),
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# ADD CAREGIVER ASSIGNMENT
# ============================================================


@admin_required
def caregiver_assignment_add(request):

    request_id = request.POST.get("homecare_request") or request.GET.get(
        "homecare_request"
    )

    selected_request = None

    if request_id:
        selected_request = get_object_or_404(
            HomeCareRequest.objects.prefetch_related("services"),
            pk=request_id,
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form = CaregiverAssignmentForm(
            request.POST,
            homecare_request=selected_request,
        )

        # ----------------------------------------------------
        # DEBUG / VALIDATION
        # ----------------------------------------------------

        if not form.is_valid():

            # Show the exact validation errors on the page.
            for field_name, errors in form.errors.items():

                for error in errors:

                    if field_name == "__all__":
                        messages.error(
                            request,
                            f"Assignment error: {error}",
                        )
                    else:
                        messages.error(
                            request,
                            f"{field_name}: {error}",
                        )

            # Also make sure the selected request is preserved.
            if selected_request is None:

                posted_request_id = request.POST.get("homecare_request")

                if posted_request_id:

                    selected_request = get_object_or_404(
                        HomeCareRequest.objects.prefetch_related("services"),
                        pk=posted_request_id,
                    )

        else:

            try:

                # ====================================================
                # CREATE ASSIGNMENT
                # ====================================================

                with transaction.atomic():

                    assignment = form.save(commit=False)

                    # ------------------------------------------------
                    # KEEP SELECTED HOME CARE REQUEST
                    # ------------------------------------------------

                    if selected_request:

                        assignment.homecare_request = selected_request

                    # ------------------------------------------------
                    # RECORD STAFF MEMBER
                    # ------------------------------------------------

                    assignment.assigned_by = request.user

                    # ------------------------------------------------
                    # NEW ASSIGNMENTS WAIT FOR ACCEPTANCE
                    # ------------------------------------------------

                    assignment.status = CaregiverAssignment.Status.PENDING

                    # ------------------------------------------------
                    # RESET RESPONSE FIELDS
                    # ------------------------------------------------

                    assignment.accepted_at = None
                    assignment.declined_at = None
                    assignment.completed_at = None
                    assignment.caregiver_response_note = ""

                    # ------------------------------------------------
                    # SAVE ASSIGNMENT
                    # ------------------------------------------------

                    assignment.save()

                    # ------------------------------------------------
                    # UPDATE HOME CARE REQUEST
                    # ------------------------------------------------

                    homecare_request = assignment.homecare_request

                    if homecare_request:

                        homecare_request.status = HomeCareRequest.Status.ASSIGNED

                        homecare_request.save(
                            update_fields=[
                                "status",
                                "updated_at",
                            ]
                        )

                # ====================================================
                # CAREGIVER REGISTRATION OR ASSIGNMENT EMAIL
                # ====================================================

                try:
                    caregiver = assignment.caregiver

                    if caregiver is None:
                        raise ValueError("No caregiver was selected.")

                    caregiver_email = (
                        getattr(caregiver, "email", None)
                        or getattr(
                            getattr(caregiver, "user", None),
                            "email",
                            None,
                        )
                        or ""
                    ).strip()

                    if not caregiver_email:
                        raise ValueError("The caregiver has no email address.")

                    user = caregiver.user

                    # -----------------------------------------------
                    # CAREGIVER HAS NOT COMPLETED REGISTRATION
                    # -----------------------------------------------
                    if user is None or not user.has_usable_password():
                        send_caregiver_registration_invitation(
                            request,
                            caregiver,
                        )

                        messages.success(
                            request,
                            (
                                "The assignment was saved. A caregiver "
                                "registration invitation was sent to "
                                f"{caregiver_email}. The caregiver must "
                                "complete registration and await approval."
                            ),
                        )

                    # -----------------------------------------------
                    # REGISTRATION COMPLETE, BUT NOT APPROVED
                    # -----------------------------------------------
                    elif (
                        caregiver.verification_status
                        != Caregiver.VerificationStatus.APPROVED
                        or not caregiver.is_active
                        or not user.is_active
                    ):
                        messages.warning(
                            request,
                            (
                                "The assignment was saved, but this "
                                "caregiver is not yet approved and active. "
                                "They must be approved before accessing "
                                "the caregiver portal."
                            ),
                        )

                    # -----------------------------------------------
                    # APPROVED AND ACTIVE
                    # -----------------------------------------------
                    else:
                        send_caregiver_assignment_email(
                            request,
                            assignment,
                        )

                        messages.success(
                            request,
                            (
                                "Assignment created successfully and "
                                "the assignment notification was sent "
                                f"to {caregiver_email}."
                            ),
                        )

                except Exception as email_error:
                    messages.error(
                        request,
                        (
                            "The assignment was saved, but the caregiver "
                            "email could not be sent. Error: "
                            f"{email_error}"
                        ),
                    )

                return redirect("staff:assignments")

            except Exception as e:

                messages.error(
                    request,
                    ("The caregiver assignment could not be " f"created. Error: {e}"),
                )

    # ========================================================
    # GET
    # ========================================================

    else:

        initial = {}

        if selected_request:

            initial["homecare_request"] = selected_request.pk

            if getattr(
                selected_request,
                "preferred_date",
                None,
            ):

                initial["service_date"] = selected_request.preferred_date

            if getattr(
                selected_request,
                "preferred_time",
                None,
            ):

                initial["service_time"] = selected_request.preferred_time

        form = CaregiverAssignmentForm(
            initial=initial,
            homecare_request=selected_request,
        )

    # ========================================================
    # REQUESTED SERVICES
    # ========================================================

    services = selected_request.services.all() if selected_request else []

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "staff/caregiver_assignment_form.html",
        {
            "form": form,
            "title": "Add Caregiver Assignment",
            "site_settings": SiteSettings.load(),
            "selected_request": selected_request,
            "requested_services": services,
        },
    )


# ============================================================
# EDIT / REASSIGN CAREGIVER
# ============================================================


@admin_required
def caregiver_assignment_edit(request, pk):

    assignment = get_object_or_404(
        CaregiverAssignment.objects.select_related(
            "caregiver",
            "homecare_request",
        ),
        pk=pk,
    )

    # Keep the original caregiver so we can determine whether
    # this was actually a reassignment.
    original_caregiver = assignment.caregiver

    if request.method == "POST":

        form = CaregiverAssignmentForm(
            request.POST,
            instance=assignment,
            homecare_request=assignment.homecare_request,
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    # ------------------------------------------------
                    # SAVE FORM WITHOUT FINAL STATUS
                    # ------------------------------------------------

                    assignment = form.save(commit=False)

                    # ------------------------------------------------
                    # RECORD STAFF MEMBER
                    # ------------------------------------------------

                    assignment.assigned_by = request.user

                    # ------------------------------------------------
                    # EVERY STAFF REASSIGNMENT RETURNS TO
                    # PENDING ACCEPTANCE
                    # ------------------------------------------------

                    assignment.status = CaregiverAssignment.Status.PENDING

                    # ------------------------------------------------
                    # RESET CAREGIVER RESPONSE
                    # ------------------------------------------------

                    assignment.accepted_at = None
                    assignment.declined_at = None
                    assignment.completed_at = None
                    assignment.caregiver_response_note = ""

                    # ------------------------------------------------
                    # SAVE
                    # ------------------------------------------------

                    assignment.save()

                    # ------------------------------------------------
                    # ENSURE HOME CARE REQUEST IS ASSIGNED
                    # ------------------------------------------------

                    homecare_request = assignment.homecare_request

                    homecare_request.status = HomeCareRequest.Status.ASSIGNED

                    homecare_request.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

                # ----------------------------------------------------
                # SEND NEW ASSIGNMENT EMAIL
                # ----------------------------------------------------

                try:

                    send_caregiver_assignment_email(
                        request,
                        assignment,
                    )

                    # Determine whether it was a reassignment.
                    if original_caregiver.pk != assignment.caregiver.pk:

                        messages.success(
                            request,
                            (
                                "Caregiver reassigned successfully. "
                                f"A new assignment notification has "
                                f"been sent to "
                                f"{assignment.caregiver.email}."
                            ),
                        )

                    else:

                        messages.success(
                            request,
                            (
                                "Caregiver assignment updated "
                                "successfully and a new assignment "
                                f"notification has been sent to "
                                f"{assignment.caregiver.email}."
                            ),
                        )

                except Exception as email_error:

                    messages.warning(
                        request,
                        (
                            "The caregiver assignment was updated "
                            "successfully, but the notification email "
                            "could not be sent. "
                            f"Email error: {email_error}"
                        ),
                    )

                return redirect("staff:assignments")

            except Exception as e:

                messages.error(
                    request,
                    ("The caregiver assignment could not be " f"updated. Error: {e}"),
                )

    else:

        form = CaregiverAssignmentForm(
            instance=assignment,
            homecare_request=assignment.homecare_request,
        )

    return render(
        request,
        "staff/caregiver_assignment_form.html",
        {
            "form": form,
            "title": "Edit Caregiver Assignment",
            "assignment": assignment,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# DELETE CAREGIVER ASSIGNMENT
# ============================================================


@admin_required
def caregiver_assignment_delete(request, pk):

    assignment = get_object_or_404(
        CaregiverAssignment,
        pk=pk,
    )

    if request.method == "POST":

        assignment.delete()

        messages.success(
            request,
            "Caregiver assignment deleted successfully.",
        )

        return redirect("staff:assignments")

    return render(
        request,
        "staff/caregiver_assignment_confirm_delete.html",
        {
            "assignment": assignment,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# HOME CARE REQUESTS
# ============================================================


@admin_required
def homecare_requests(request):

    current_status = request.GET.get(
        "status",
        "",
    ).strip()

    search = request.GET.get(
        "q",
        "",
    ).strip()

    requests_queryset = HomeCareRequest.objects.prefetch_related("services").order_by(
        "-created_at"
    )

    if search:

        requests_queryset = requests_queryset.filter(
            Q(full_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
            | Q(address__icontains=search)
            | Q(city__icontains=search)
        )

    if current_status:

        requests_queryset = requests_queryset.filter(status=current_status)

    return render(
        request,
        "staff/homecare_requests.html",
        {
            "homecare_requests": requests_queryset,
            "current_status": current_status,
            "search": search,
            "status_choices": (HomeCareRequest.Status.choices),
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# ADD HOME CARE REQUEST
# ============================================================


@admin_required
def homecare_request_add(request):

    if request.method == "POST":

        form = HomeCareRequestForm(request.POST)

        if form.is_valid():

            homecare_request = form.save(commit=False)

            if not homecare_request.status:

                homecare_request.status = HomeCareRequest.Status.NEW

            homecare_request.save()

            form.save_m2m()

            messages.success(
                request,
                (
                    f"Home care request for "
                    f'"{homecare_request.full_name}" '
                    f"has been created successfully."
                ),
            )

            return redirect("staff:homecare_requests")

    else:

        form = HomeCareRequestForm(initial={"status": HomeCareRequest.Status.NEW})

    return render(
        request,
        "staff/homecare_request_form.html",
        {
            "form": form,
            "title": "Create Home Care Request",
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# EDIT HOME CARE REQUEST
# ============================================================


@admin_required
def homecare_request_edit(request, pk):

    homecare_request = get_object_or_404(
        HomeCareRequest,
        pk=pk,
    )

    if request.method == "POST":

        form = HomeCareRequestForm(
            request.POST,
            instance=homecare_request,
        )

        if form.is_valid():

            homecare_request = form.save()

            messages.success(
                request,
                (
                    f"Home care request for "
                    f'"{homecare_request.full_name}" '
                    f"has been updated successfully."
                ),
            )

            return redirect("staff:homecare_requests")

    else:

        form = HomeCareRequestForm(
            instance=homecare_request,
        )

    return render(
        request,
        "staff/homecare_request_form.html",
        {
            "form": form,
            "homecare_request": homecare_request,
            "title": (f"Edit Home Care Request - " f"{homecare_request.full_name}"),
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# DELETE HOME CARE REQUEST
# ============================================================


@admin_required
def homecare_request_delete(request, pk):

    homecare_request = get_object_or_404(
        HomeCareRequest,
        pk=pk,
    )

    if request.method == "POST":

        patient_name = homecare_request.full_name

        homecare_request.delete()

        messages.success(
            request,
            (
                f"Home care request for "
                f'"{patient_name}" '
                f"has been deleted successfully."
            ),
        )

        return redirect("staff:homecare_requests")

    return render(
        request,
        "staff/homecare_request_confirm_delete.html",
        {
            "homecare_request": homecare_request,
        },
    )


# ============================================================
# REFERRALS
# ============================================================


@admin_required
def referrals(request):

    current_status = request.GET.get(
        "status",
        "",
    ).strip()

    search = request.GET.get(
        "q",
        "",
    ).strip()

    total_referrals = Referral.objects.count()

    pending_referrals = Referral.objects.filter(
        status="PENDING",
    ).count()

    completed_referrals = Referral.objects.filter(
        status="COMPLETED",
    ).count()

    referrals_queryset = (
        Referral.objects.select_related(
            "homecare_request",
        )
        .prefetch_related(
            "services_needed",
            "attachments",
        )
        .order_by(
            "-created_at",
        )
    )

    if search:

        referrals_queryset = referrals_queryset.filter(
            Q(referrer_name__icontains=search)
            | Q(referrer_email__icontains=search)
            | Q(referrer_phone__icontains=search)
            | Q(referring_facility__icontains=search)
            | Q(patient_name__icontains=search)
            | Q(patient_email__icontains=search)
            | Q(patient_phone__icontains=search)
        ).distinct()

    if current_status:

        referrals_queryset = referrals_queryset.filter(
            status=current_status,
        )

    context = {
        "referrals": referrals_queryset,
        "total_referrals": total_referrals,
        "pending_referrals": pending_referrals,
        "completed_referrals": completed_referrals,
        "current_status": current_status,
        "search": search,
        "status_choices": Referral.Status.choices,
        "site_settings": SiteSettings.load(),
    }

    return render(
        request,
        "staff/referrals.html",
        context,
    )


# ============================================================
# APPOINTMENTS / CONSULTATIONS
# ============================================================


@admin_required
def appointments(request):

    current_status = request.GET.get(
        "status",
        "",
    )

    appointment_id = request.GET.get(
        "appointment",
        "",
    ).strip()

    appointments_queryset = Consultation.objects.select_related("doctor").order_by(
        "-created_at"
    )

    if current_status:

        appointments_queryset = appointments_queryset.filter(status=current_status)

    if appointment_id:

        if appointment_id.isdigit():

            appointments_queryset = appointments_queryset.filter(pk=appointment_id)

    return render(
        request,
        "staff/appointments.html",
        {
            "appointments": appointments_queryset,
            "current_status": current_status,
            "selected_appointment_id": appointment_id,
            "status_choices": (Consultation.Status.choices),
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# QUOTATIONS
# ============================================================


@admin_required
def quotations(request):

    quotations_queryset = Quotation.objects.select_related(
        "homecare_request",
        "consultation",
    ).order_by("-created_at")

    return render(
        request,
        "staff/quotations.html",
        {
            "quotations": quotations_queryset,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# STAFF QUOTATION DETAIL
# ============================================================


@admin_required
def quotation_detail(request, pk):

    quotation = get_object_or_404(
        Quotation.objects.select_related(
            "homecare_request",
            "consultation",
        ),
        pk=pk,
    )

    return render(
        request,
        "staff/quotation_detail.html",
        {
            "quotation": quotation,
        },
    )


# ============================================================
# PAYMENTS
# ============================================================


@admin_required
def payments(request):

    payment_admin = admin.site._registry[Payment]

    extra_context = {
        "opts": Payment._meta,
        "app_label": Payment._meta.app_label,
        "title": "Payment Management",
        "site_settings": SiteSettings.load(),
    }

    original_template = payment_admin.change_list_template

    payment_admin.change_list_template = "staff/payments.html"

    try:

        return payment_admin.changelist_view(
            request,
            extra_context=extra_context,
        )

    finally:

        payment_admin.change_list_template = original_template


# ============================================================
# PAYMENT VERIFICATION
# ============================================================


@admin_required
def payment_verify(request, payment_id):

    payment = get_object_or_404(
        Payment.objects.select_related(
            "quotation",
            "quotation__homecare_request",
            "quotation__consultation",
            "verified_by",
        ),
        pk=payment_id,
    )

    quotation = payment.quotation

    homecare_request = getattr(
        quotation,
        "homecare_request",
        None,
    )

    consultation = getattr(
        quotation,
        "consultation",
        None,
    )

    client_name = ""

    if homecare_request:

        client_name = getattr(
            homecare_request,
            "full_name",
            "",
        )

    elif consultation:

        client_name = str(consultation)

    if request.method == "POST":

        return homecare_verify_payment(
            request,
            payment_id,
        )

    context = {
        "payment": payment,
        "quotation": quotation,
        "homecare_request": homecare_request,
        "consultation": consultation,
        "client_name": client_name,
        "site_settings": SiteSettings.load(),
    }

    return render(
        request,
        "homecare/payment_verify.html",
        context,
    )


# ============================================================
# PAYMENT DETAIL
# ============================================================


@admin_required
def payment_detail(request, pk):

    payment = get_object_or_404(
        Payment.objects.select_related(
            "quotation",
            "quotation__homecare_request",
            "quotation__consultation",
            "verified_by",
        ),
        pk=pk,
    )

    return render(
        request,
        "staff/payment_detail.html",
        {
            "payment": payment,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# CAREGIVER DAILY REPORTS
# ============================================================


@admin_required
def caregiver_daily_reports(request):

    condition = request.GET.get(
        "condition",
        "",
    ).strip()

    search = request.GET.get(
        "q",
        "",
    ).strip()

    reports_queryset = CaregiverDailyReport.objects.select_related(
        "assignment",
        "assignment__caregiver",
        "assignment__homecare_request",
        "reviewed_by",
    ).order_by(
        "-report_date",
        "-submitted_at",
    )

    if search:

        reports_queryset = reports_queryset.filter(
            Q(assignment__caregiver__name__icontains=search)
            | Q(assignment__caregiver__user__first_name__icontains=search)
            | Q(assignment__caregiver__user__last_name__icontains=search)
        )

    if condition:

        reports_queryset = reports_queryset.filter(patient_condition=condition)

    condition_field = CaregiverDailyReport._meta.get_field("patient_condition")

    condition_choices = condition_field.choices

    return render(
        request,
        "staff/reports.html",
        {
            "reports": reports_queryset,
            "condition": condition,
            "search": search,
            "condition_choices": condition_choices,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# ADD CAREGIVER DAILY REPORT
# ============================================================


@admin_required
def caregiver_daily_report_add(request):

    if request.method == "POST":

        form = CaregiverDailyReportForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Caregiver daily report created successfully.",
            )

            return redirect("staff:reports")

    else:

        form = CaregiverDailyReportForm()

    return render(
        request,
        "staff/caregiver_daily_report_form.html",
        {
            "form": form,
            "title": "Add Caregiver Daily Report",
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# EDIT CAREGIVER DAILY REPORT
# ============================================================


@admin_required
def caregiver_daily_report_edit(request, pk):

    report = get_object_or_404(
        CaregiverDailyReport,
        pk=pk,
    )

    if request.method == "POST":

        form = CaregiverDailyReportForm(
            request.POST,
            instance=report,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Caregiver daily report updated successfully.",
            )

            return redirect("staff:reports")

    else:

        form = CaregiverDailyReportForm(
            instance=report,
        )

    return render(
        request,
        "staff/caregiver_daily_report_form.html",
        {
            "form": form,
            "title": "Edit Caregiver Daily Report",
            "report": report,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# DELETE CAREGIVER DAILY REPORT
# ============================================================


@admin_required
def caregiver_daily_report_delete(request, pk):

    report = get_object_or_404(
        CaregiverDailyReport,
        pk=pk,
    )

    if request.method == "POST":

        report.delete()

        messages.success(
            request,
            "Caregiver daily report deleted successfully.",
        )

        return redirect("staff:reports")

    return render(
        request,
        "staff/caregiver_daily_report_confirm_delete.html",
        {
            "report": report,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# CAREGIVER PAYMENTS
# ============================================================


@admin_required
def caregiver_payments(request):

    current_status = request.GET.get(
        "status",
        "",
    ).strip()

    search = request.GET.get(
        "q",
        "",
    ).strip()

    payments_queryset = CaregiverPayment.objects.select_related(
        "caregiver",
        "assignment",
        "assignment__homecare_request",
    ).order_by("-created_at")

    if search:

        payments_queryset = payments_queryset.filter(
            Q(caregiver__name__icontains=search)
            | Q(caregiver__user__first_name__icontains=search)
            | Q(caregiver__user__last_name__icontains=search)
            | Q(caregiver__user__email__icontains=search)
        )

    if current_status:

        payments_queryset = payments_queryset.filter(status=current_status)

    status_field = CaregiverPayment._meta.get_field("status")

    status_choices = status_field.choices

    return render(
        request,
        "staff/caregiver_payments.html",
        {
            "payments": payments_queryset,
            "current_status": current_status,
            "search": search,
            "status_choices": status_choices,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# ADD CAREGIVER PAYMENT
# ============================================================


@admin_required
def caregiver_payment_add(request):

    if request.method == "POST":

        form = CaregiverPaymentForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Caregiver payment created successfully.",
            )

            return redirect("staff:caregiver_payments")

    else:

        form = CaregiverPaymentForm()

    return render(
        request,
        "staff/caregiver_payment_form.html",
        {
            "form": form,
            "title": "Add Caregiver Payment",
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# EDIT CAREGIVER PAYMENT
# ============================================================


@admin_required
def caregiver_payment_edit(request, pk):

    payment = get_object_or_404(
        CaregiverPayment,
        pk=pk,
    )

    if request.method == "POST":

        form = CaregiverPaymentForm(
            request.POST,
            instance=payment,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Caregiver payment updated successfully.",
            )

            return redirect("staff:caregiver_payments")

    else:

        form = CaregiverPaymentForm(
            instance=payment,
        )

    return render(
        request,
        "staff/caregiver_payment_form.html",
        {
            "form": form,
            "title": "Edit Caregiver Payment",
            "payment": payment,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# DELETE CAREGIVER PAYMENT
# ============================================================


@admin_required
def caregiver_payment_delete(request, pk):

    payment = get_object_or_404(
        CaregiverPayment,
        pk=pk,
    )

    if request.method == "POST":

        payment.delete()

        messages.success(
            request,
            "Caregiver payment deleted successfully.",
        )

        return redirect("staff:caregiver_payments")

    return render(
        request,
        "staff/caregiver_payment_confirm_delete.html",
        {
            "payment": payment,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# SERVICES
# ============================================================


@admin_required
def services(request):

    search = request.GET.get(
        "q",
        "",
    ).strip()

    category = request.GET.get(
        "category",
        "",
    ).strip()

    active = request.GET.get(
        "active",
        "",
    ).strip()

    services_queryset = (
        Service.objects.select_related("category")
        .all()
        .order_by(
            "order",
            "name",
        )
    )

    if search:

        services_queryset = services_queryset.filter(
            Q(name__icontains=search)
            | Q(category__name__icontains=search)
            | Q(short_description__icontains=search)
            | Q(description__icontains=search)
        )

    if category:

        services_queryset = services_queryset.filter(category_id=category)

    if active == "yes":

        services_queryset = services_queryset.filter(is_active=True)

    elif active == "no":

        services_queryset = services_queryset.filter(is_active=False)

    categories = ServiceCategory.objects.all().order_by(
        "order",
        "name",
    )

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        selected_ids = request.POST.getlist("selected_services")

        if not selected_ids:

            messages.warning(
                request,
                "Please select at least one service.",
            )

            return redirect("staff:services")

        selected_services = Service.objects.filter(id__in=selected_ids)

        if action == "activate":

            updated = selected_services.update(is_active=True)

            messages.success(
                request,
                f"{updated} service(s) activated successfully.",
            )

        elif action == "deactivate":

            updated = selected_services.update(is_active=False)

            messages.success(
                request,
                f"{updated} service(s) deactivated successfully.",
            )

        elif action == "delete":

            count = selected_services.count()

            selected_services.delete()

            messages.success(
                request,
                f"{count} service(s) deleted successfully.",
            )

        else:

            messages.warning(
                request,
                "Please select a valid action.",
            )

        return redirect("staff:services")

    return render(
        request,
        "staff/services.html",
        {
            "services": services_queryset,
            "categories": categories,
            "search": search,
            "current_category": category,
            "current_active": active,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# ADD SERVICE
# ============================================================


@admin_required
def service_add(request):

    categories = ServiceCategory.objects.all().order_by("order", "name")

    if request.method == "POST":

        post_data = request.POST.copy()
        new_category_name = post_data.get("new_category", "").strip()

        created_category = None

        if new_category_name:

            new_category_name = new_category_name[:150]

            category = ServiceCategory.objects.filter(
                name__iexact=new_category_name
            ).first()

            if category is None:
                category = ServiceCategory.objects.create(name=new_category_name)
                created_category = category

            post_data["category"] = str(category.pk)

        form = ServiceForm(
            post_data,
            request.FILES,
        )

        if form.is_valid():

            try:
                service = form.save()

                messages.success(
                    request,
                    f'"{service.name}" has been added successfully.',
                )

                return redirect("staff:services")

            except Exception as error:

                messages.error(
                    request,
                    f"Service could not be saved: {error}",
                )

        else:

            for field_name, errors in form.errors.items():

                for error in errors:

                    if field_name == "__all__":
                        messages.error(
                            request,
                            f"Service error: {error}",
                        )
                    else:
                        messages.error(
                            request,
                            f"{field_name}: {error}",
                        )

        if created_category:

            if not Service.objects.filter(category=created_category).exists():

                created_category.delete()

        categories = ServiceCategory.objects.all().order_by("order", "name")

    else:

        form = ServiceForm()

    return render(
        request,
        "staff/service_form.html",
        {
            "form": form,
            "title": "Add Service",
            "categories": categories,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# EDIT SERVICE
# ============================================================


@admin_required
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)

    categories = ServiceCategory.objects.all().order_by("order", "name")

    if request.method == "POST":
        post_data = request.POST.copy()
        new_category_name = post_data.get("new_category", "").strip()
        created_category = None

        if new_category_name:
            new_category_name = new_category_name[:150]
            category = ServiceCategory.objects.filter(
                name__iexact=new_category_name
            ).first()

            if category is None:
                category = ServiceCategory.objects.create(name=new_category_name)
                created_category = category

            post_data["category"] = str(category.pk)

        form = ServiceForm(
            post_data,
            request.FILES,
            instance=service,
        )

        if form.is_valid():
            service = form.save()
            messages.success(
                request,
                f'"{service.name}" has been updated successfully.',
            )
            return redirect("staff:services")

        for field_name, errors in form.errors.items():
            for error in errors:
                if field_name == "__all__":
                    messages.error(request, f"Service error: {error}")
                else:
                    messages.error(request, f"{field_name}: {error}")

        # Remove a newly created category if validation failed and
        # no service uses it.
        if (
            created_category
            and not Service.objects.filter(category=created_category).exists()
        ):
            created_category.delete()

        # Refresh the category list so a newly created category that
        # remains in use is included in the form.
        categories = ServiceCategory.objects.all().order_by("order", "name")

    else:
        form = ServiceForm(instance=service)

    return render(
        request,
        "staff/service_form.html",
        {
            "form": form,
            "service": service,
            "title": f"Edit Service - {service.name}",
            "categories": categories,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# DELETE SERVICE
# ============================================================


@admin_required
def service_delete(request, pk):

    service = get_object_or_404(
        Service,
        pk=pk,
    )

    if request.method == "POST":

        service_name = service.name

        service.delete()

        messages.success(
            request,
            f'"{service_name}" has been deleted successfully.',
        )

        return redirect("staff:services")

    return render(
        request,
        "staff/service_confirm_delete.html",
        {
            "service": service,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# STAFF SETTINGS
# ============================================================


@admin_required
def settings(request):

    site_settings = SiteSettings.load()

    if request.method == "POST":

        form = SiteSettingsForm(
            request.POST,
            request.FILES,
            instance=site_settings,
        )

        if form.is_valid():

            site_settings = form.save()

            messages.success(
                request,
                "Site settings have been updated successfully.",
            )

            return redirect("staff:settings")

    else:

        form = SiteSettingsForm(
            instance=site_settings,
        )

    return render(
        request,
        "staff/settings.html",
        {
            "form": form,
            "settings": site_settings,
            "site_settings": site_settings,
        },
    )


# ============================================================
# ADD CAREGIVER
# ============================================================


@admin_required
@require_http_methods(["GET", "POST"])
def caregiver_add(request):

    form = StaffCaregiverInviteForm(request.POST or None)

    if request.method == "POST":

        if form.is_valid():

            email = form.cleaned_data["email"].strip().lower()

            # -------------------------------------------------
            # CHECK EXISTING USER
            # -------------------------------------------------

            existing_user = User.objects.filter(email__iexact=email).first()

            if existing_user:

                messages.error(
                    request,
                    (
                        "A user account already exists with "
                        f"the email address {email}."
                    ),
                )

                return render(
                    request,
                    "staff/caregiver_add.html",
                    {
                        "form": form,
                    },
                )

            # -------------------------------------------------
            # CHECK EXISTING CAREGIVER
            # -------------------------------------------------

            existing_caregiver = Caregiver.objects.filter(email__iexact=email).first()

            if existing_caregiver:

                messages.error(
                    request,
                    ("A caregiver profile already exists " f"for {email}."),
                )

                return render(
                    request,
                    "staff/caregiver_add.html",
                    {
                        "form": form,
                    },
                )

            with transaction.atomic():

                # -------------------------------------------------
                # CREATE USER WITHOUT PASSWORD
                # -------------------------------------------------

                user = User(
                    email=email,
                    first_name="",
                    last_name="",
                    role=User.Role.CAREGIVER,
                    is_active=False,
                )

                # The caregiver will create their own password.
                user.set_unusable_password()

                # If your custom User still requires username,
                # generate a unique internal username.
                if hasattr(user, "username"):

                    username_base = email.split("@")[0]

                    username = username_base
                    counter = 1

                    while User.objects.filter(username=username).exists():

                        username = f"{username_base}" f"{counter}"

                        counter += 1

                    user.username = username

                user.save()

                # -------------------------------------------------
                # CREATE CAREGIVER PROFILE
                # -------------------------------------------------

                caregiver = form.save(commit=False)

                caregiver.user = user

                caregiver.name = form.cleaned_data["name"]

                caregiver.email = email

                caregiver.is_active = False

                caregiver.verification_status = Caregiver.VerificationStatus.PENDING

                caregiver.save()

                # -------------------------------------------------
                # INVALIDATE PREVIOUS INVITATIONS
                # -------------------------------------------------

                CaregiverInvitation.objects.filter(
                    caregiver=caregiver,
                    used_at__isnull=True,
                ).update(used_at=timezone.now())

                # -------------------------------------------------
                # GENERATE SECURE TOKEN
                # -------------------------------------------------

                token = secrets.token_urlsafe(48)

                invitation = CaregiverInvitation.objects.create(
                    caregiver=caregiver,
                    email=email,
                    token=token,
                    expires_at=(timezone.now() + timedelta(days=3)),
                    created_by=request.user,
                )

            # -------------------------------------------------
            # BUILD REGISTRATION URL
            # -------------------------------------------------

            registration_url = request.build_absolute_uri(
                reverse(
                    "caregivers:register_invitation",
                    kwargs={
                        "token": invitation.token,
                    },
                )
            )

            # -------------------------------------------------
            # SEND INVITATION EMAIL
            # -------------------------------------------------

            business_name = "Hands-On Health"

            subject = f"{business_name} Caregiver Registration Invitation"

            message = f"""
Hello {caregiver.name},

You have been invited to complete your caregiver registration
with {business_name}.

Please use the secure link below to complete your profile:

{registration_url}

This invitation expires in 3 days.

You will be asked to:

- Confirm your personal information
- Create your own password
- Provide your professional information
- Upload your CV
- Upload your licence document
- Upload professional certificates

Your caregiver account will remain inactive until your profile
has been reviewed and approved by {business_name}.

If you did not expect this invitation, please contact
{business_name}.

Kind regards,

{business_name}
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    None,
                ),
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(
                request,
                (
                    f"Caregiver profile created and "
                    f"registration invitation sent to {email}."
                ),
            )

            return redirect("staff:caregivers")

    return render(
        request,
        "staff/caregiver_add.html",
        {
            "form": form,
        },
    )


# ============================================================
# RESEND CAREGIVER REGISTRATION INVITATION
# ============================================================


@admin_required
@require_http_methods(["POST"])
def caregiver_send_invitation(request, pk):
    caregiver = get_object_or_404(
        Caregiver.objects.select_related("user"),
        pk=pk,
    )

    if caregiver.verification_status != Caregiver.VerificationStatus.PENDING:
        messages.warning(
            request,
            "Invitations can only be resent to pending caregivers.",
        )
        return redirect("staff:caregivers")

    if caregiver.user and caregiver.user.has_usable_password():
        messages.info(
            request,
            "This caregiver has completed registration. Please review the application.",
        )
        return redirect("staff:caregiver_verify", pk=caregiver.pk)

    email = (
        (
            getattr(caregiver, "email", None)
            or getattr(caregiver.user, "email", None)
            or ""
        )
        .strip()
        .lower()
    )

    if not email:
        messages.error(
            request,
            "This caregiver has no email address.",
        )
        return redirect("staff:caregivers")

    if not caregiver.user:
        messages.error(
            request,
            "This caregiver has no linked user account. Create or repair the account before sending an invitation.",
        )
        return redirect("staff:caregivers")

    now = timezone.now()

    active_invitation = (
        CaregiverInvitation.objects.filter(
            caregiver=caregiver,
            used_at__isnull=True,
            expires_at__gt=now,
        )
        .order_by("-expires_at")
        .first()
    )

    # Do not resend before the current invitation expires.
    if active_invitation:
        messages.info(
            request,
            "The invitation is still valid. You can resend it after its three-day expiry.",
        )
        return redirect("staff:caregivers")

    try:
        with transaction.atomic():
            # Mark old, unused invitations as no longer usable.
            CaregiverInvitation.objects.filter(
                caregiver=caregiver,
                used_at__isnull=True,
            ).update(used_at=now)

            invitation = CaregiverInvitation.objects.create(
                caregiver=caregiver,
                email=email,
                token=secrets.token_urlsafe(48),
                expires_at=now + timedelta(days=3),
                created_by=request.user,
            )

            registration_url = request.build_absolute_uri(
                reverse(
                    "caregivers:register_invitation",
                    kwargs={"token": invitation.token},
                )
            )

            send_mail(
                subject="Hands-On Health Caregiver Registration Invitation",
                message=f"""
Hello {caregiver.name},

Please complete your caregiver registration with Hands-On Health
using the secure link below:

{registration_url}

This invitation expires in 3 days.

After completing registration, your application will be reviewed
by an administrator before your account is activated.

Kind regards,
Hands-On Health
""",
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    None,
                ),
                recipient_list=[email],
                fail_silently=False,
            )

    except Exception as exc:
        messages.error(
            request,
            f"The invitation could not be sent: {exc}",
        )
        return redirect("staff:caregivers")

    messages.success(
        request,
        f"A new three-day registration invitation was sent to {email}.",
    )
    return redirect("staff:caregivers")


@require_http_methods(["GET", "POST"])
def ask_question(request):
    page = QuestionFormSettings.load()

    if not page.is_active:
        return render(
            request,
            "staff/questions/form_disabled.html",
            status=503,
        )

    if request.method == "POST":
        name = request.POST.get("ask_name", "").strip()
        email = request.POST.get("ask_email", "").strip()
        phone = request.POST.get("ask_phone", "").strip()
        topic = request.POST.get("question_topic", "general").strip()
        question = request.POST.get("user_question", "").strip()

        valid_topics = {
            item["value"]
            for item in page.topics
            if isinstance(item, dict) and item.get("value") and item.get("label")
        }

        if not all([name, email, phone, question]):
            messages.error(
                request,
                "Please complete all required fields.",
            )
        elif topic not in valid_topics:
            messages.error(
                request,
                "Please select a valid question topic.",
            )
        else:
            CustomerQuestion.objects.create(
                name=name,
                email=email,
                phone=phone,
                topic=topic,
                question=question,
            )

            messages.success(
                request,
                "Your question has been submitted successfully. "
                "Our team will get back to you.",
            )
            return redirect("pages:faq")

    return render(
        request,
        "staff/questions/ask_question.html",
        {"question_page": page},
    )


# ============================================================
# CUSTOMER QUESTIONS DASHBOARD
# ============================================================


@admin_required
def questions_dashboard_view(request):

    new_count = CustomerQuestion.objects.filter(
        status=CustomerQuestion.Status.NEW
    ).count()

    active_faqs_count = FAQItem.objects.filter(is_active=True).count()

    context = {
        "new_count": new_count,
        "active_faqs_count": active_faqs_count,
        "site_settings": SiteSettings.load(),
    }

    return render(
        request,
        "staff/questions/faqdashboard.html",
        context,
    )


@admin_required
def question_inbox(request):
    questions = CustomerQuestion.objects.all()

    status = request.GET.get("status", "").strip()
    search = request.GET.get("q", "").strip()

    valid_statuses = {choice[0] for choice in CustomerQuestion.Status.choices}

    if status in valid_statuses:
        questions = questions.filter(status=status)

    if search:
        from django.db.models import Q

        questions = questions.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(question__icontains=search)
        )

    context = {
        "questions": questions,
        "selected_status": status,
        "search_query": search,
        "new_count": CustomerQuestion.objects.filter(
            status=CustomerQuestion.Status.NEW
        ).count(),
        "in_progress_count": CustomerQuestion.objects.filter(
            status=CustomerQuestion.Status.IN_PROGRESS
        ).count(),
        "replied_count": CustomerQuestion.objects.filter(
            status=CustomerQuestion.Status.REPLIED
        ).count(),
    }

    return render(
        request,
        "staff/questions/inbox.html",
        context,
    )


@admin_required
@require_http_methods(["GET", "POST"])
def question_reply(request, question_id):
    question = get_object_or_404(
        CustomerQuestion,
        pk=question_id,
    )

    if request.method == "POST":
        reply = request.POST.get("staff_reply", "").strip()
        action = request.POST.get("action", "save").strip()

        if action == "close":
            question.status = CustomerQuestion.Status.CLOSED
            question.save(update_fields=["status", "updated_at"])

            messages.success(request, "Question closed successfully.")

            return redirect("staff:question_inbox")

        if action not in {"save", "send"}:
            messages.error(request, "Invalid action.")

        elif not reply:
            messages.error(request, "Please enter a reply.")

        else:
            # Store the reply before attempting email delivery.
            question.staff_reply = reply
            question.replied_by = request.user

            if action == "save":
                question.status = CustomerQuestion.Status.IN_PROGRESS
                question.save()

                messages.success(request, "Reply draft saved successfully.")

                return redirect(
                    "staff:question_reply",
                    question_id=question.pk,
                )

            # Send the branded HTML email.
            try:
                context = {
                    "customer_name": question.name,
                    "customer_question": question.question,
                    "staff_response": reply,
                }

                html_content = render_to_string(
                    "staff/questions/email/answer_notification.html",
                    context,
                )

                text_content = (
                    f"Dear {question.name},\n\n"
                    "Thank you for contacting Hands-On Health.\n\n"
                    "Your question:\n"
                    f"{question.question}\n\n"
                    "Our response:\n"
                    f"{reply}\n\n"
                    "Kind regards,\n"
                    "Hands-On Health Team"
                )

                email = EmailMultiAlternatives(
                    subject=("Your Question Has Been Answered | Hands-On Health"),
                    body=text_content,
                    from_email=(getattr(settings, "DEFAULT_FROM_EMAIL", None) or None),
                    to=[question.email],
                )

                email.attach_alternative(
                    html_content,
                    "text/html",
                )

                email.send(fail_silently=False)

            except Exception as exc:
                # Log the actual error in the Django terminal.
                logger.exception(
                    "Question reply email failed for question %s",
                    question.pk,
                )

                # Preserve the draft and keep the question open.
                question.status = CustomerQuestion.Status.IN_PROGRESS
                question.save()

                # Show a friendly message to the staff user.
                messages.error(
                    request,
                    "The reply was saved, but the email could not be sent. "
                    "Check the Django terminal for the exact error.",
                )

                return redirect(
                    "staff:question_reply",
                    question_id=question.pk,
                )

            # Update the status only after the email backend accepts it.
            question.status = CustomerQuestion.Status.REPLIED
            question.replied_at = timezone.now()
            question.save()

            messages.success(
                request,
                f"Reply emailed successfully to {question.email}.",
            )

            return redirect(
                "staff:question_reply",
                question_id=question.pk,
            )

    # Always return a response for GET and invalid POST submissions.
    return render(
        request,
        "staff/questions/reply.html",
        {"question": question},
    )


@admin_required
def faq_list(request):
    """List and search FAQs in the staff dashboard."""
    faqs = FAQItem.objects.all().order_by("display_order", "id")

    search = request.GET.get("q", "").strip()
    if search:
        from django.db.models import Q

        faqs = faqs.filter(Q(question__icontains=search) | Q(answer__icontains=search))

    return render(
        request,
        "staff/questions/faq_list.html",
        {
            "faqs": faqs,
            "search": search,
            "total_faqs": FAQItem.objects.count(),
            "active_faqs": FAQItem.objects.filter(is_active=True).count(),
        },
    )


# ============================================================
# CREATE FAQ
# ============================================================


@admin_required
@require_http_methods(["GET", "POST"])
def faq_create(request):
    """Create a new public FAQ."""

    if request.method == "POST":

        question = request.POST.get("question", "").strip()

        answer = request.POST.get("answer", "").strip()

        display_order = request.POST.get("display_order", "0").strip()

        is_active = request.POST.get("is_active", "").strip().lower() in (
            "on",
            "true",
            "1",
            "yes",
        )

        if not question or not answer:

            messages.error(request, "Enter both a question and its answer.")

        else:

            try:
                order = int(display_order or 0)

                if order < 0:
                    raise ValueError

            except ValueError:

                messages.error(
                    request, "Display order must be zero or a positive number."
                )

            else:

                faq = FAQItem.objects.create(
                    question=question,
                    answer=answer,
                    display_order=order,
                    is_active=is_active,
                )

                messages.success(request, f'FAQ "{faq.question}" added successfully.')

                return redirect("staff:faq_list")

    return render(
        request,
        "staff/questions/faq_form.html",
        {
            "page_title": "Add FAQ",
            "faq": None,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# EDIT FAQ
# ============================================================


@admin_required
@require_http_methods(["GET", "POST"])
def faq_edit(request, pk):
    """Edit an existing FAQ."""

    faq = get_object_or_404(
        FAQItem,
        pk=pk,
    )

    if request.method == "POST":

        question = request.POST.get("question", "").strip()

        answer = request.POST.get("answer", "").strip()

        display_order = request.POST.get("display_order", "0").strip()

        is_active = request.POST.get("is_active", "").strip().lower() in (
            "on",
            "true",
            "1",
            "yes",
        )

        if not question or not answer:

            messages.error(request, "Enter both a question and its answer.")

        else:

            try:
                order = int(display_order or 0)

                if order < 0:
                    raise ValueError

            except ValueError:

                messages.error(
                    request, "Display order must be zero or a positive number."
                )

            else:

                faq.question = question
                faq.answer = answer
                faq.display_order = order
                faq.is_active = is_active

                faq.save()

                messages.success(request, f'FAQ "{faq.question}" updated successfully.')

                return redirect("staff:faq_list")

    return render(
        request,
        "staff/questions/faq_form.html",
        {
            "page_title": "Edit FAQ",
            "faq": faq,
            "site_settings": SiteSettings.load(),
        },
    )


@admin_required
def faq_delete(request, pk):
    """Delete an FAQ after a confirmation."""
    faq = get_object_or_404(FAQItem, pk=pk)

    if request.method == "POST":
        faq.delete()
        messages.success(request, "FAQ deleted successfully.")
        return redirect("staff:faq_list")

    return render(
        request,
        "staff/questions/faq_delete.html",
        {
            "faq": faq,
        },
    )


@admin_required
def contact_enquiries(request):
    """Display public website contact submissions."""

    enquiries = ContactEnquiry.objects.select_related("service").order_by("-created_at")

    return render(
        request,
        "staff/contact_enquiries.html",
        {
            "enquiries": enquiries,
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def contact_enquiry_reply(request, pk):
    enquiry = get_object_or_404(ContactEnquiry, pk=pk)

    if request.method == "POST":
        reply_text = request.POST.get("reply", "").strip()

        if not reply_text:
            messages.error(request, "Please enter a reply message.")
            return redirect("staff:contact_enquiry_reply", pk=pk)

        site = SiteSettings.load()
        business = site.business_name or "Hands-On Health"

        subject = f"Re: Your Enquiry | {business}"

        plain_body = (
            f"Dear {enquiry.name},\n\n"
            f"Thank you for contacting {business}.\n\n"
            f"{reply_text}\n\n"
            f"Kind regards,\n"
            f"{business} Team"
        )

        safe_name = escape(enquiry.name)
        safe_business = escape(business)
        safe_reply = escape(reply_text).replace("\n", "<br>")

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:30px 12px;
                     background:#f1f6fb;
                     font-family:Arial,sans-serif;">

          <table role="presentation" width="100%"
                 cellpadding="0" cellspacing="0">
            <tr>
              <td align="center">
                <table role="presentation" width="600"
                       cellpadding="0" cellspacing="0"
                       style="max-width:600px;width:100%;
                              background:#ffffff;
                              border-radius:14px;overflow:hidden;">

                  <tr>
                    <td style="background:#103b70;
                               padding:30px;text-align:center;">
                      <h2 style="color:white;margin:0;">
                        {safe_business}
                      </h2>
                      <p style="color:#c6e6ff;margin:10px 0 0;">
                        Home-Based Healthcare
                      </p>
                    </td>
                  </tr>

                  <tr>
                    <td style="padding:35px 30px;">
                      <h2 style="color:#103b70;">
                        Thank You for Contacting Us
                      </h2>

                      <p>Dear {safe_name},</p>

                      <p>
                        Thank you for reaching out to
                        {safe_business}.
                      </p>

                      <div style="background:#f0f8ff;
                                  border-left:4px solid #1689d2;
                                  padding:20px;
                                  border-radius:6px;
                                  line-height:1.8;
                                  overflow-wrap:anywhere;">
                        {safe_reply}
                      </div>

                      <p style="margin-top:25px;">
                        Kind regards,<br>
                        <strong>{safe_business} Team</strong>
                      </p>
                    </td>
                  </tr>

                  <tr>
                    <td style="background:#eaf4fc;
                               text-align:center;
                               padding:20px;
                               font-size:12px;
                               color:#54718a;">
                      Compassionate Care. Professional Support.
                    </td>
                  </tr>

                </table>
              </td>
            </tr>
          </table>

        </body>
        </html>
        """

        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_body,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[enquiry.email],
            )

            email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=False)

        except Exception:
            logger.exception(
                "Failed to reply to contact enquiry %s",
                enquiry.pk,
            )
            messages.error(
                request,
                "The reply could not be sent. Please try again.",
            )
            return redirect("staff:contact_enquiry_reply", pk=pk)

        # Change status ONLY after email.send() succeeds.
        enquiry.status = ContactEnquiry.Status.CONTACTED
        enquiry.save(update_fields=["status", "updated_at"])

        messages.success(
            request,
            "Reply sent successfully. Enquiry marked as Contacted.",
        )
        return redirect("staff:contact_enquiries")

    return render(
        request,
        "staff/contact_enquiry_reply.html",
        {"enquiry": enquiry},
    )


# ============================================================
# STAFF ACTIVITY NOTIFICATIONS (CONFIGURED RECIPIENTS ONLY)
# ============================================================
# These receivers are registered when staff.views is loaded by staff.urls.
# They send staff activity alerts only; caregiver/client emails remain unchanged.

import re as _notification_re
from django.conf import settings as _notification_django_settings
from django.db.models.signals import post_save as _notification_post_save
from django.core.validators import validate_email as _notification_validate_email
from django.core.exceptions import ValidationError as _NotificationValidationError


def _send_configured_staff_alert(subject, description, dashboard_url_name, record_id):
    """Queue an alert for SiteSettings.notification_emails ONLY."""
    try:
        site = SiteSettings.load()
        raw = getattr(site, "notification_emails", "") or ""
        recipients = []
        seen = set()
        for candidate in _notification_re.split(r"[,;\n]+", raw):
            email = candidate.strip()
            if not email or email.lower() in seen:
                continue
            try:
                _notification_validate_email(email)
            except _NotificationValidationError:
                logger.warning("Skipping invalid staff notification email: %s", email)
                continue
            seen.add(email.lower())
            recipients.append(email)

        # Intentionally no fallback to SiteSettings.email.
        if not recipients:
            logger.info(
                "Staff activity alert skipped: no notification emails configured."
            )
            return

        base_url = (getattr(site, "website", "") or "").strip().rstrip("/") or (
            getattr(_notification_django_settings, "SITE_URL", "") or ""
        ).strip().rstrip("/")
        if not base_url or not base_url.startswith(("https://", "http://")):
            logger.warning(
                "Staff alert skipped: set SiteSettings.website or SITE_URL to an absolute URL."
            )
            return

        path = reverse(dashboard_url_name)
        url = f"{base_url}{path}"
        business = site.business_name or "Hands-On Health"
        body = (
            f"Hello {business} Team,\n\n"
            f"{description}\n\n"
            f"Record ID: {record_id}\n\n"
            f"Open staff dashboard: {url}\n\n"
            "Please sign in to review this item.\n\n"
            f"{business} - Automated staff notification"
        )

        def _deliver():
            safe_business = escape(business)
            safe_subject = escape(subject)
            safe_description = escape(description)
            safe_url = escape(url)

            html_body = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>{safe_subject}</title>
            </head>

            <body style="margin:0;padding:0;background:#f1f6fb;
                         font-family:Arial,Helvetica,sans-serif;color:#243b53;">

                <table role="presentation" cellpadding="0" cellspacing="0"
                       width="100%" style="background:#f1f6fb;padding:35px 12px;">
                    <tr>
                        <td align="center">

                            <table role="presentation" cellpadding="0" cellspacing="0"
                                   width="600"
                                   style="width:100%;max-width:600px;background:#ffffff;
                                          border-radius:16px;overflow:hidden;">

                                <tr>
                                    <td style="background:#103b70;padding:32px 35px;
                                               text-align:center;">

                                        <h1 style="margin:0;color:#ffffff;font-size:25px;
                                                   line-height:1.4;">
                                            {safe_business}
                                        </h1>

                                        <p style="color:#b9e4ff;font-size:13px;
                                                  margin:10px 0 0;">
                                            PROFESSIONAL HOME-BASED HEALTHCARE
                                        </p>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:35px 35px 15px;">

                                        <p style="font-size:12px;font-weight:bold;
                                                  letter-spacing:1px;color:#1689d2;">
                                            STAFF ACTIVITY NOTIFICATION
                                        </p>

                                        <h2 style="font-size:25px;color:#103b70;
                                                   margin:12px 0 18px;">
                                            {safe_subject}
                                        </h2>

                                        <p style="font-size:15px;line-height:1.8;">
                                            Hello {safe_business} Team,
                                        </p>

                                        <p style="font-size:15px;line-height:1.8;">
                                            {safe_description}
                                        </p>

                                        <table role="presentation" width="100%"
                                               cellpadding="0" cellspacing="0"
                                               style="background:#edf7ff;
                                                      border-left:4px solid #1689d2;
                                                      border-radius:8px;
                                                      margin:25px 0;">
                                            <tr>
                                                <td style="padding:20px;">
                                                    <p style="margin:0;color:#54718a;
                                                              font-size:13px;">
                                                        REFERENCE NUMBER
                                                    </p>
                                                    <p style="margin:8px 0 0;
                                                              font-size:23px;
                                                              font-weight:bold;
                                                              color:#103b70;">
                                                        #{escape(str(record_id))}
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>

                                        <p style="font-size:15px;line-height:1.7;">
                                            Please sign in to the staff dashboard
                                            to review this notification and take
                                            any necessary action.
                                        </p>

                                        <table role="presentation" cellpadding="0"
                                               cellspacing="0"
                                               style="margin:30px 0;">
                                            <tr>
                                                <td bgcolor="#087bd5"
                                                    style="border-radius:8px;">
                                                    <a href="{safe_url}"
                                                       style="display:inline-block;
                                                              padding:16px 28px;
                                                              color:#ffffff;
                                                              font-size:15px;
                                                              font-weight:bold;
                                                              text-decoration:none;">
                                                        Open Staff Dashboard &rarr;
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>

                                        <p style="font-size:12px;line-height:1.7;
                                                  color:#71869a;overflow-wrap:anywhere;">
                                            If the button does not work, use this link:
                                            <a href="{safe_url}"
                                               style="color:#087bd5;">
                                                {safe_url}
                                            </a>
                                        </p>

                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:25px 35px;
                                               border-top:1px solid #e5edf4;">

                                        <p style="font-size:14px;line-height:1.7;
                                                  color:#54718a;margin:0;">
                                            Thank you for helping us deliver
                                            compassionate, professional care.
                                        </p>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="background:#eaf4fc;padding:25px;
                                               text-align:center;">

                                        <p style="font-size:15px;font-weight:bold;
                                                  color:#103b70;margin:0;">
                                            {safe_business}
                                        </p>

                                        <p style="font-size:12px;color:#637f96;
                                                  margin:10px 0 0;">
                                            Automated Staff Notification
                                        </p>

                                        <p style="font-size:11px;color:#8295a6;
                                                  margin:10px 0 0;">
                                            This message was generated automatically.
                                            Please do not reply to this email.
                                        </p>
                                    </td>
                                </tr>

                            </table>

                        </td>
                    </tr>
                </table>

            </body>
            </html>
            """

            for email in recipients:
                try:
                    message = EmailMultiAlternatives(
                        subject=f"{business} | {subject}",
                        body=body,
                        from_email=getattr(
                            _notification_django_settings,
                            "DEFAULT_FROM_EMAIL",
                            None,
                        ),
                        to=[email],
                    )

                    message.attach_alternative(html_body, "text/html")
                    message.send(fail_silently=False)
                except Exception:
                    logger.exception(
                        "Staff notification email failed for %s",
                        email,
                    )

        transaction.on_commit(_deliver)
    except Exception:
        # Never interrupt a client submission because a notification fails.
        logger.exception("Could not prepare staff activity notification")


def _staff_homecare_created(sender, instance, created, **kwargs):
    if created:
        _send_configured_staff_alert(
            "New Home Care Request",
            "A new home care request has been submitted.",
            "staff:homecare_requests",
            instance.pk,
        )


def _staff_appointment_created(sender, instance, created, **kwargs):
    if created:
        _send_configured_staff_alert(
            "New Appointment / Consultation",
            "A new appointment or consultation has been submitted.",
            "staff:appointments",
            instance.pk,
        )


def _staff_referral_created(sender, instance, created, **kwargs):
    if created:
        _send_configured_staff_alert(
            "New Patient Referral",
            "A new patient referral has been submitted.",
            "staff:referrals",
            instance.pk,
        )


def _staff_payment_created(sender, instance, created, **kwargs):
    if created:
        _send_configured_staff_alert(
            "New Payment Record",
            "A new payment record has been created. Review its verification status.",
            "staff:payments",
            instance.pk,
        )


def _staff_question_created(sender, instance, created, **kwargs):
    if created:
        _send_configured_staff_alert(
            "New Customer FAQ Question",
            "A customer has submitted a new FAQ question.",
            "staff:question_inbox",
            instance.pk,
        )


def _staff_contact_enquiry_created(sender, instance, created, **kwargs):
    if created:
        _send_configured_staff_alert(
            "New Contact Enquiry",
            "A visitor has submitted a new contact enquiry through the website.",
            "staff:contact_enquiries",
            instance.pk,
        )


_notification_post_save.connect(
    _staff_homecare_created,
    sender=HomeCareRequest,
    dispatch_uid="staff_alert_homecare_created_v1",
    weak=False,
)
_notification_post_save.connect(
    _staff_appointment_created,
    sender=Consultation,
    dispatch_uid="staff_alert_appointment_created_v1",
    weak=False,
)
_notification_post_save.connect(
    _staff_referral_created,
    sender=Referral,
    dispatch_uid="staff_alert_referral_created_v1",
    weak=False,
)
_notification_post_save.connect(
    _staff_payment_created,
    sender=Payment,
    dispatch_uid="staff_alert_payment_created_v1",
    weak=False,
)
_notification_post_save.connect(
    _staff_question_created,
    sender=CustomerQuestion,
    dispatch_uid="staff_alert_question_created_v1",
    weak=False,
)

_notification_post_save.connect(
    _staff_contact_enquiry_created,
    sender=ContactEnquiry,
    dispatch_uid="staff_alert_contact_enquiry_created_v1",
    weak=False,
)


# ============================================================
# TESTIMONIAL MANAGEMENT
# ============================================================


@admin_required
def testimonials(request):
    """List testimonials for staff moderation."""

    current_status = request.GET.get("status", "").strip()
    search = request.GET.get("q", "").strip()

    testimonials_queryset = Testimonial.objects.all().order_by("-created_at")

    if current_status in {value for value, label in Testimonial.Status.choices}:
        testimonials_queryset = testimonials_queryset.filter(status=current_status)
    else:
        current_status = ""

    if search:
        testimonials_queryset = testimonials_queryset.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(message__icontains=search)
        )

    context = {
        "testimonials": testimonials_queryset,
        "current_status": current_status,
        "search": search,
        "status_choices": Testimonial.Status.choices,
        "pending_testimonials": Testimonial.objects.filter(
            status=Testimonial.Status.PENDING
        ).count(),
        "site_settings": SiteSettings.load(),
    }

    return render(
        request,
        "staff/testimonials.html",
        context,
    )


@admin_required
@require_http_methods(["POST"])
def testimonial_moderate(request, pk):
    """Approve or reject a testimonial."""
    testimonial = get_object_or_404(Testimonial, pk=pk)
    action = request.POST.get("action", "").strip().lower()

    if action == "approve":
        if not testimonial.consent_to_publish:
            messages.error(
                request,
                "This testimonial cannot be published without consent.",
            )
            return redirect("staff:testimonials")

        testimonial.approve()
        messages.success(request, "Testimonial approved successfully.")

    elif action == "reject":
        testimonial.reject()
        messages.success(request, "Testimonial rejected successfully.")

    else:
        messages.error(request, "Please select a valid moderation action.")

    return redirect("staff:testimonials")


@admin_required
def about_us_edit(request):
    # Reuse the existing Founder record.
    founder = Founder.objects.order_by("pk").first()

    # Create a record only if none exists.
    if founder is None:
        founder = Founder.objects.create()

    if request.method == "POST":
        form = FounderForm(
            request.POST,
            request.FILES,
            instance=founder,
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "About Us information updated successfully.",
            )
            return redirect("staff:about_us_edit")

        messages.error(
            request,
            "Please correct the errors below.",
        )
    else:
        form = FounderForm(instance=founder)

    return render(
        request,
        "staff/about_us_form.html",
        {
            "form": form,
            "founder": founder,
            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# HERO SLIDER MANAGEMENT
# ============================================================

HERO_DEFAULTS = {
    1: {
        "tagline": "Compassionate • Reliable • Dignified",
        "heading": "Quality Care in the Comfort & Dignity of Home",
        "description": (
            "Professional mobile nursing and personal care for "
            "elderly, recovering, and dependent loved ones across Namibia."
        ),
    },
    2: {
        "tagline": "Professional Nursing Support",
        "heading": "Clinical Care Beyond Hospital Walls",
        "description": (
            "Vital signs monitoring, wound dressing, post-surgery "
            "recovery, and chronic condition management at home."
        ),
    },
    3: {
        "tagline": "Support for Patients & Families",
        "heading": "Dependable Assistance Tailored Around You",
        "description": (
            "Dedicated daily living support, bedridden care, and "
            "extended family respite delivered with genuine respect."
        ),
    },
}


@admin_required
def hero_slides(request):
    # Ensure there is one database record for each slide.
    for position, defaults in HERO_DEFAULTS.items():
        HeroSlide.objects.get_or_create(
            position=position,
            defaults=defaults,
        )

    slides = HeroSlide.objects.all()

    return render(
        request,
        "staff/hero_slides.html",
        {
            "slides": slides,
            "site_settings": SiteSettings.load(),
        },
    )


@admin_required
def hero_slide_edit(request, position):
    if position not in (1, 2, 3):
        from django.http import Http404

        raise Http404("Hero slide not found.")

    slide, created = HeroSlide.objects.get_or_create(
        position=position,
        defaults=HERO_DEFAULTS[position],
    )

    if request.method == "POST":
        form = HeroSlideForm(
            request.POST,
            request.FILES,
            instance=slide,
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Slide {position} updated successfully.",
            )
            return redirect("staff:hero_slides")

        messages.error(
            request,
            "Please correct the errors below.",
        )
    else:
        form = HeroSlideForm(instance=slide)

    return render(
        request,
        "staff/hero_slide_form.html",
        {
            "form": form,
            "slide": slide,
            "site_settings": SiteSettings.load(),
        },
    )
