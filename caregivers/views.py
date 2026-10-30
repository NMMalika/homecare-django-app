import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from homecare.models import CaregiverPayment
from django.db.models import Sum
from decimal import Decimal

from accounts.models import User

from homecare.models import (
    Caregiver,
    CaregiverCertificate,
    CaregiverAssignment,
    CaregiverInvitation,
)

from .forms import (
    CaregiverLoginForm,
    CaregiverInvitationRegistrationForm,
    CaregiverPublicApplicationForm,
)


logger = logging.getLogger(__name__)


# ============================================================
# SHARED HELPERS
# ============================================================

def _get_caregiver_for_user(user):
    """Return the caregiver profile linked to a user, if it exists."""
    try:
        return user.caregiver_profile
    except Caregiver.DoesNotExist:
        return None


def _get_sender_email():
    """Return the configured default sender email."""
    return getattr(settings, "DEFAULT_FROM_EMAIL", None)


def _get_staff_emails():
    """
    Get active administrator email addresses.
    Fall back to Django's ADMINS setting if necessary.
    """
    emails = list(
        User.objects.filter(
            role=User.Role.ADMIN,
            is_active=True,
        )
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )

    if not emails:
        emails = [
            email
            for name, email in getattr(settings, "ADMINS", [])
            if email
        ]

    return list(dict.fromkeys(emails))


def _send_email(subject, message, recipients):
    """
    Send an email without allowing an email failure to undo
    a successfully saved registration.
    """
    recipients = list(
        dict.fromkeys(
            email.strip()
            for email in recipients
            if email and email.strip()
        )
    )

    if not recipients:
        return False

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=_get_sender_email(),
            recipient_list=recipients,
            fail_silently=False,
        )
        return True

    except Exception:
        logger.exception("Email delivery failed: %s", subject)
        return False


# ============================================================
# CAREGIVER LOGIN
# ============================================================

@require_http_methods(["GET", "POST"])
def caregiver_login(request):
    """
    Only approved and active caregiver accounts may log in.
    """

    # Already authenticated users
    if request.user.is_authenticated:
        if getattr(request.user, "role", None) == User.Role.CAREGIVER:
            caregiver = _get_caregiver_for_user(request.user)

            if (
                caregiver
                and caregiver.is_active
                and caregiver.verification_status
                == Caregiver.VerificationStatus.APPROVED
            ):
                return redirect("caregivers:dashboard")

            logout(request)
        else:
            logout(request)

    # Login form
    form = CaregiverLoginForm(
        request,
        data=request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        # Check role
        if getattr(user, "role", None) != User.Role.CAREGIVER:
            messages.error(
                request,
                "This login is for caregivers only.",
            )
            return redirect("caregivers:login")

        # Get caregiver profile
        caregiver = _get_caregiver_for_user(user)

        if caregiver is None:
            messages.error(
                request,
                "Your caregiver profile could not be found. "
                "Please contact the administrator.",
            )
            return redirect("caregivers:login")

        # Check verification before allowing access
        if (
            caregiver.verification_status
            != Caregiver.VerificationStatus.APPROVED
        ):
            messages.warning(
                request,
                "Thank you for registering. Your application is "
                "awaiting administrator approval. You will receive "
                "an email with the login link and confirmation "
                "once your application is approved.",
            )
            return redirect("caregivers:login")

        # Check profile and user account activation
        if not caregiver.is_active or not user.is_active:
            messages.error(
                request,
                "Your caregiver account is not currently active. "
                "Please contact the administrator if you believe "
                "your application has already been approved.",
            )
            return redirect("caregivers:login")

        # Authenticate caregiver
        login(request, user)

        next_url = (
            request.POST.get("next")
            or request.GET.get("next")
        )

        # Only allow safe redirects to this website
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)

        messages.success(
            request,
            f"Welcome back, {caregiver.name}.",
        )
        return redirect("caregivers:dashboard")

    return render(
        request,
        "caregivers/login.html",
        {"form": form},
    )


# ============================================================
# CAREGIVER REGISTRATION VIA INVITATION
# ============================================================

@require_http_methods(["GET", "POST"])
def caregiver_register_invitation(request, token):
    """
    Complete caregiver registration using an invitation.

    Successful registration:
    1. Saves personal information and uploaded documents.
    2. Keeps the caregiver and user account inactive.
    3. Sets verification status to PENDING.
    4. Marks the invitation as used.
    5. Sends a thank-you email to the caregiver.
    6. Notifies staff that the application is ready for review.

    The caregiver receives the login link in the approval email
    sent by the staff approval view, not in the initial email.
    """

    invitation = get_object_or_404(
        CaregiverInvitation,
        token=token,
    )

    # --------------------------------------------------------
    # INVALID INVITATION PAGE HELPER
    # --------------------------------------------------------

    def invalid_invitation_page(title, message):
        return render(
            request,
            "caregivers/register.html",
            {
                "invitation_invalid": True,
                "invalid_title": title,
                "invalid_message": message,
                "site_settings": getattr(
                    request,
                    "site_settings",
                    None,
                ),
            },
        )

    # --------------------------------------------------------
    # CHECK WHETHER INVITATION HAS BEEN USED
    # --------------------------------------------------------

    if invitation.used_at is not None:
        return invalid_invitation_page(
            "Invitation Already Used",
            "This invitation has already been used. Please contact "
            "Hands-On Health if you need assistance.",
        )

    # --------------------------------------------------------
    # CHECK EXPIRATION
    # --------------------------------------------------------

    if timezone.now() >= invitation.expires_at:
        return invalid_invitation_page(
            "Invitation Expired",
            "This invitation has expired. Please contact "
            "Hands-On Health to request a new invitation.",
        )

    caregiver = invitation.caregiver

    # --------------------------------------------------------
    # PREVENT DUPLICATE REGISTRATION
    # --------------------------------------------------------

    if (
        caregiver.user
        and caregiver.user.has_usable_password()
    ):
        return invalid_invitation_page(
            "Registration Already Completed",
            "Your registration has already been completed. Your "
            "application must be approved before you can access "
            "the caregiver portal.",
        )

    # --------------------------------------------------------
    # REGISTRATION FORM
    # --------------------------------------------------------

    form = CaregiverInvitationRegistrationForm(
        request.POST or None,
        request.FILES or None,
        caregiver=caregiver,
    )

    # --------------------------------------------------------
    # PROCESS SUBMISSION
    # --------------------------------------------------------

    if request.method == "POST" and form.is_valid():

        try:
            with transaction.atomic():

                # Lock the invitation to prevent duplicate use
                locked_invitation = (
                    CaregiverInvitation.objects
                    .select_for_update()
                    .get(pk=invitation.pk)
                )

                locked_caregiver = (
                    Caregiver.objects
                    .select_for_update()
                    .get(pk=caregiver.pk)
                )

                # Recheck invitation after locking
                if locked_invitation.used_at is not None:
                    messages.error(
                        request,
                        "This invitation has already been used.",
                    )
                    return redirect("caregivers:login")

                if timezone.now() >= locked_invitation.expires_at:
                    messages.error(
                        request,
                        "This invitation has expired. Please contact staff.",
                    )
                    return redirect("caregivers:login")

                # Get linked user
                user = locked_caregiver.user

                if user is None:
                    messages.error(
                        request,
                        "Your caregiver account could not be found. "
                        "Please contact Hands-On Health.",
                    )
                    return redirect("caregivers:login")

                if user.has_usable_password():
                    messages.error(
                        request,
                        "Registration has already been completed.",
                    )
                    return redirect("caregivers:login")

                # --------------------------------------------
                # SAVE USER DETAILS
                # --------------------------------------------

                user.first_name = (
                    form.cleaned_data["first_name"].strip()
                )
                user.last_name = (
                    form.cleaned_data["last_name"].strip()
                )
                user.email = locked_invitation.email.strip().lower()
                user.role = User.Role.CAREGIVER

                # User must remain inactive until approval
                user.is_active = False
                user.set_password(form.cleaned_data["password"])

                user.save(
                    update_fields=[
                        "first_name",
                        "last_name",
                        "email",
                        "role",
                        "is_active",
                        "password",
                    ]
                )

                # --------------------------------------------
                # SAVE CAREGIVER PERSONAL DETAILS
                # --------------------------------------------

                locked_caregiver.name = (
                    f"{user.first_name} {user.last_name}"
                ).strip()

                locked_caregiver.email = user.email

                locked_caregiver.phone = (
                    form.cleaned_data.get("phone")
                    or locked_caregiver.phone
                    or ""
                ).strip()

                locked_caregiver.professional_title = (
                    form.cleaned_data.get("professional_title")
                    or ""
                ).strip()

                locked_caregiver.specialization = (
                    form.cleaned_data.get("specialization")
                    or ""
                ).strip()

                locked_caregiver.licence_number = (
                    form.cleaned_data.get("licence_number")
                    or ""
                ).strip()

                locked_caregiver.licence_issuing_authority = (
                    form.cleaned_data.get(
                        "licence_issuing_authority"
                    )
                    or ""
                ).strip()

                locked_caregiver.licence_expiry_date = (
                    form.cleaned_data.get("licence_expiry_date")
                )

                # --------------------------------------------
                # CV UPLOAD
                # --------------------------------------------

                cv_file = form.cleaned_data.get("cv")
                if cv_file:
                    locked_caregiver.cv = cv_file

                # --------------------------------------------
                # COVER LETTER UPLOAD
                # --------------------------------------------

                cover_letter_file = form.cleaned_data.get(
                    "cover_letter"
                )
                if cover_letter_file:
                    locked_caregiver.cover_letter = (
                        cover_letter_file
                    )

                # --------------------------------------------
                # LICENCE DOCUMENT UPLOAD
                # --------------------------------------------

                licence_document_file = form.cleaned_data.get(
                    "licence_document"
                )
                if licence_document_file:
                    locked_caregiver.licence_document = (
                        licence_document_file
                    )

                # --------------------------------------------
                # KEEP PROFILE PENDING AND INACTIVE
                # --------------------------------------------

                locked_caregiver.verification_status = (
                    Caregiver.VerificationStatus.PENDING
                )
                locked_caregiver.is_active = False
                locked_caregiver.save()

                # --------------------------------------------
                # SAVE CERTIFICATE UPLOADS
                # --------------------------------------------

                certificate_files = (
                    form.cleaned_data.get("certificates") or []
                )

                if not isinstance(certificate_files, (list, tuple)):
                    certificate_files = [certificate_files]

                for certificate_file in certificate_files:
                    if not certificate_file:
                        continue

                    CaregiverCertificate.objects.create(
                        caregiver=locked_caregiver,
                        certificate_name=certificate_file.name,
                        document=certificate_file,
                    )

                # --------------------------------------------
                # MARK INVITATION AS USED
                # --------------------------------------------

                locked_invitation.used_at = timezone.now()
                locked_invitation.save(
                    update_fields=["used_at"]
                )

                # Keep saved instances for notifications
                caregiver = locked_caregiver
                invitation = locked_invitation

            # =================================================
            # REGISTRATION IS NOW COMMITTED TO THE DATABASE
            # SEND EMAILS OUTSIDE THE TRANSACTION
            # =================================================

            caregiver_name = caregiver.name or "Caregiver"
            caregiver_email = (
                caregiver.email or invitation.email or ""
            ).strip().lower()

            staff_directory_url = request.build_absolute_uri(
                reverse("staff:caregivers")
            )

            # --------------------------------------------
            # EMAIL 1: THANK-YOU EMAIL TO CAREGIVER
            # --------------------------------------------

            caregiver_email_sent = _send_email(
                subject=(
                    "Registration Received - Hands-On Health"
                ),
                message=f"""Dear {caregiver_name},

Thank you for completing your caregiver registration with
Hands-On Health.

We have successfully received your registration details
and supporting documents.

Your application is now awaiting administrator verification.
You do not need to register again.

Once our administration team has reviewed and approved your
application, you will receive a separate approval email
containing the caregiver login link.

Your account remains inactive until it has been approved.

Thank you for your interest in joining Hands-On Health.

Kind regards,
Hands-On Health
""",
                recipients=[caregiver_email],
            )

            # --------------------------------------------
            # EMAIL 2: NOTIFY STAFF
            # --------------------------------------------

            staff_emails = _get_staff_emails()

            staff_email_sent = _send_email(
                subject=(
                    "New Caregiver Registration - "
                    f"{caregiver_name}"
                ),
                message=f"""Hello Hands-On Health Administration Team,

A caregiver has completed registration and is awaiting verification.

CAREGIVER DETAILS
-----------------
Name: {caregiver.name}
Email: {caregiver_email}
Phone: {caregiver.phone}
Professional title: {caregiver.professional_title or "Not provided"}
Specialization: {caregiver.specialization or "Not provided"}
Licence number: {caregiver.licence_number or "Not provided"}
Licence issuing authority: {caregiver.licence_issuing_authority or "Not provided"}
Licence expiry date: {caregiver.licence_expiry_date or "Not provided"}

VERIFICATION STATUS
-------------------
{caregiver.get_verification_status_display()}

Please sign in to the staff dashboard and review the
caregiver's submitted information and supporting documents.

Staff caregiver directory:
{staff_directory_url}

The caregiver account must remain inactive until an
administrator approves the application.

Kind regards,
Hands-On Health Registration System
""",
                recipients=staff_emails,
            )

            # --------------------------------------------
            # SUCCESS MESSAGE
            # --------------------------------------------

            messages.success(
                request,
                "Thank you for registering with Hands-On Health! "
                "Your registration and documents have been received. "
                "Your application is awaiting administrator verification. "
                "You will receive an email with the caregiver login link "
                "once your application is approved.",
            )

            if not caregiver_email_sent:
                messages.warning(
                    request,
                    "Your registration was saved successfully, but "
                    "the thank-you email could not be sent. Please "
                    "contact Hands-On Health if you need assistance.",
                )

            if not staff_email_sent:
                messages.warning(
                    request,
                    "Your registration was saved successfully, but "
                    "the staff notification email could not be sent. "
                    "Please check the email configuration and "
                    "administrator email addresses.",
                )

            return redirect("caregivers:login")

        except Exception:
            logger.exception(
                "Caregiver invitation registration failed for token %s",
                token,
            )

            messages.error(
                request,
                "We could not complete your registration. Please check "
                "your information and uploaded documents, then try again. "
                "If the problem continues, contact Hands-On Health.",
            )

    # ========================================================
    # PREFILL INVITATION DETAILS
    # ========================================================

    invited_name = (caregiver.name or "").strip()
    name_parts = invited_name.split(maxsplit=1)

    invited_first_name = (
        name_parts[0] if name_parts else ""
    )
    invited_last_name = (
        name_parts[1] if len(name_parts) > 1 else ""
    )

    # ========================================================
    # DISPLAY REGISTRATION PAGE
    # ========================================================

    return render(
        request,
        "caregivers/register.html",
        {
            "form": form,
            "invitation": invitation,
            "caregiver": caregiver,
            "invited_name": caregiver.name,
            "invited_first_name": invited_first_name,
            "invited_last_name": invited_last_name,
            "invited_phone": caregiver.phone,
            "invited_email": invitation.email,
            "is_invitation_registration": True,
            "site_settings": getattr(
                request,
                "site_settings",
                None,
            ),
        },
    )


# ============================================================
# CAREGIVER DASHBOARD
# ============================================================

# ============================================================
# CAREGIVER DASHBOARD
# ASSIGNMENTS + APPROVED PAYMENTS
# ============================================================


@login_required
def caregiver_dashboard(request):
    """
    Display the logged-in caregiver's:
    - Assignments
    - Assignment statistics
    - Approved caregiver payments
    - Payment totals and history
    """

    # --------------------------------------------------------
    # CHECK USER ROLE
    # --------------------------------------------------------

    if getattr(request.user, "role", None) != User.Role.CAREGIVER:
        messages.error(
            request,
            "Only caregiver accounts can access this dashboard.",
        )
        return redirect("caregivers:login")

    # --------------------------------------------------------
    # GET LOGGED-IN CAREGIVER
    # --------------------------------------------------------

    caregiver = _get_caregiver_for_user(request.user)

    if caregiver is None:
        messages.error(
            request,
            "Your caregiver profile could not be found.",
        )
        return redirect("caregivers:login")

    # --------------------------------------------------------
    # VERIFY ACCOUNT APPROVAL
    # --------------------------------------------------------

    if (
        not request.user.is_active
        or not caregiver.is_active
        or caregiver.verification_status != Caregiver.VerificationStatus.APPROVED
    ):
        logout(request)

        messages.warning(
            request,
            "Your caregiver account is not currently approved and active.",
        )

        return redirect("caregivers:login")

    # --------------------------------------------------------
    # CAREGIVER ASSIGNMENTS
    # --------------------------------------------------------

    assignments = list(
        CaregiverAssignment.objects.filter(caregiver=caregiver)
        .select_related("homecare_request")
        .order_by("-assigned_at", "-id")
    )

    pending_count = 0
    active_count = 0
    completed_count = 0

    for assignment in assignments:

        status = str(assignment.status).upper()

        if status in ("PENDING", "PENDING_ACCEPTANCE"):
            pending_count += 1

        elif status in ("ACCEPTED", "IN_PROGRESS", "ASSIGNED"):
            active_count += 1

        elif status == "COMPLETED":
            completed_count += 1

    # --------------------------------------------------------
    # PAYMENT STATUS CONFIGURATION
    # --------------------------------------------------------

    # Only show statuses actually defined in the payment model.
    valid_statuses = {value for value, label in CaregiverPayment.Status.choices}

    visible_statuses = [
        status for status in ("APPROVED", "PAID") if status in valid_statuses
    ]

    # --------------------------------------------------------
    # CAREGIVER PAYMENT HISTORY
    # --------------------------------------------------------

    approved_payments = (
        CaregiverPayment.objects.filter(
            caregiver=caregiver,
            status__in=visible_statuses,
            assignment__caregiver=caregiver,
        )
        .select_related(
            "assignment",
            "assignment__homecare_request",
        )
        .order_by("-created_at", "-pk")
    )

    # --------------------------------------------------------
    # PAYMENT STATISTICS
    # --------------------------------------------------------

    approved_payment_count = approved_payments.count()

    approved_total = approved_payments.aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0.00")

    paid_payments = approved_payments.filter(status="PAID")

    paid_total = paid_payments.aggregate(total=Sum("amount"))["total"] or Decimal(
        "0.00"
    )

    awaiting_payment_total = approved_payments.filter(status="APPROVED").aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    recent_payments = approved_payments[:5]

    # --------------------------------------------------------
    # DASHBOARD CONTEXT
    # --------------------------------------------------------

    context = {
        "caregiver": caregiver,
        # Assignments
        "assignments": assignments,
        "pending_count": pending_count,
        "active_count": active_count,
        "completed_count": completed_count,
        # Payments
        "approved_payments": approved_payments,
        "recent_payments": recent_payments,
        "approved_payment_count": approved_payment_count,
        "approved_total": approved_total,
        "paid_total": paid_total,
        "awaiting_payment_total": awaiting_payment_total,
    }

    return render(
        request,
        "caregivers/dashboard.html",
        context,
    )


# ============================================================
# CAREGIVER PROFILE
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def caregiver_profile(request):
    """Allow an approved caregiver to view and update basic details."""

    if getattr(request.user, "role", None) != User.Role.CAREGIVER:
        messages.error(
            request,
            "Only caregivers can access this page.",
        )
        return redirect("caregivers:login")

    caregiver = _get_caregiver_for_user(request.user)

    if caregiver is None:
        messages.error(
            request,
            "Your caregiver profile could not be found.",
        )
        return redirect("caregivers:login")

    if (
        not request.user.is_active
        or not caregiver.is_active
        or caregiver.verification_status
        != Caregiver.VerificationStatus.APPROVED
    ):
        logout(request)
        messages.warning(
            request,
            "Your caregiver account is not currently approved and active.",
        )
        return redirect("caregivers:login")

    if request.method == "POST":
        caregiver.name = request.POST.get(
            "name",
            caregiver.name or "",
        ).strip()

        caregiver.professional_title = request.POST.get(
            "professional_title",
            caregiver.professional_title or "",
        ).strip()

        caregiver.specialization = request.POST.get(
            "specialization",
            caregiver.specialization or "",
        ).strip()

        caregiver.phone = request.POST.get(
            "phone",
            caregiver.phone or "",
        ).strip()

        new_email = request.POST.get(
            "email",
            caregiver.email or "",
        ).strip().lower()

        # Keep the user account and caregiver profile emails aligned.
        request.user.email = new_email
        request.user.save(update_fields=["email"])
        caregiver.email = new_email

        if request.FILES.get("cv"):
            caregiver.cv = request.FILES["cv"]

        caregiver.save()

        messages.success(
            request,
            "Your profile has been updated successfully.",
        )
        return redirect("caregivers:profile")

    return render(
        request,
        "caregivers/profile.html",
        {"caregiver": caregiver},
    )


# ============================================================
# CAREGIVER LOGOUT
# ============================================================

@require_http_methods(["GET", "POST"])
def caregiver_logout(request):
    """Log out the current user."""

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully.",
    )

    return redirect("caregivers:login")


def caregiver_public_apply(request):
    """
    Public caregiver application.
    Applicants do not need an invitation.
    Applications remain inactive until staff approval.
    """
    if request.method == "POST":
        form = CaregiverPublicApplicationForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            data = form.cleaned_data
            email = data["email"].strip().lower()

            try:
                with transaction.atomic():
                    # Create a caregiver account, but do not allow login yet.
                    user = User(
                        username=email,
                        email=email,
                        first_name=data["first_name"].strip(),
                        last_name=data["last_name"].strip(),
                        phone=data.get("phone", "").strip(),
                        role=User.Role.CAREGIVER,
                        is_active=False,
                    )
                    user.set_password(data["password"])
                    user.save()

                    # Save the application for staff review.
                    caregiver = Caregiver.objects.create(
                        user=user,
                        name=f"{user.first_name} {user.last_name}".strip(),
                        professional_title=data.get("professional_title", ""),
                        specialization=data.get("specialization", ""),
                        phone=data.get("phone", ""),
                        email=email,
                        licence_number=data.get("licence_number", ""),
                        licence_issuing_authority=data.get(
                            "licence_issuing_authority", ""
                        ),
                        licence_expiry_date=data.get("licence_expiry_date") or None,
                        cv=data.get("cv"),
                        cover_letter=data.get("cover_letter"),
                        licence_document=data.get("licence_document"),
                        verification_status=Caregiver.VerificationStatus.PENDING,
                        is_active=False,
                    )

                    # Save uploaded certificates.
                    certificates = data.get("certificates") or []

                    for uploaded_file in certificates:
                        certificate_name = os.path.splitext(uploaded_file.name)[0][:255]

                        CaregiverCertificate.objects.create(
                            caregiver=caregiver,
                            certificate_name=certificate_name
                            or "Supporting Certificate",
                            document=uploaded_file,
                        )

                    caregiver.certificate_submitted = bool(certificates)
                    caregiver.save(
                        update_fields=[
                            "certificate_submitted",
                            "updated_at",
                        ]
                    )

            except Exception:
                # Keep database changes atomic and avoid exposing
                # internal errors to applicants.
                form.add_error(
                    None,
                    "We could not submit your application right now. "
                    "Please try again or contact Hands-On Health.",
                )
            else:
                # Notify the applicant.
                send_mail(
                    subject="Caregiver application received - Hands-On Health",
                    message=(
                        f"Dear {user.first_name},\n\n"
                        "Thank you for applying to join Hands-On Health.\n\n"
                        "We have received your caregiver application. "
                        "Your account will remain inactive while our team "
                        "reviews your application and supporting documents.\n\n"
                        "We will contact you when a decision has been made.\n\n"
                        "Kind regards,\n"
                        "Hands-On Health"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )

                # Notify the staff responsible for reviewing applications.
                staff_emails = _get_staff_emails()

                if staff_emails:
                    send_mail(
                        subject="New caregiver application requires review",
                        message=(
                            "A new caregiver application has been submitted.\n\n"
                            f"Applicant: {user.get_full_name()}\n"
                            f"Email: {email}\n"
                            f"Phone: {caregiver.phone}\n"
                            f"Professional title: "
                            f"{caregiver.professional_title}\n"
                            f"Specialization: {caregiver.specialization}\n\n"
                            "Please open the staff dashboard to review "
                            "the application and supporting documents."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=staff_emails,
                        fail_silently=True,
                    )

                return redirect("caregivers:application_success")

    else:
        form = CaregiverPublicApplicationForm()

    return render(
        request,
        "caregivers/public_apply.html",
        {"form": form},
    )


def caregiver_application_success(request):
    return render(
        request,
        "caregivers/application_success.html",
    )
