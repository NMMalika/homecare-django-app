from datetime import datetime, timedelta
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from core.models import SiteSettings

from .forms import (
    HomeCareRequestForm,
    PaymentSubmissionForm,
    QuotationForm,
    QuotationItemFormSet,
    ReferralForm,
)

from .models import (
    HomeCareRequest,
    HomeCareRequestAttachment,
    Quotation,
    Referral,
    ReferralAttachment,
    Payment,
    Caregiver,
    CaregiverAssignment,
    CaregiverDailyReport,
    CaregiverWeeklyReport,
    Consultation,
    ConsultationAttachment,
    ConsultationSlot,
)

logger = logging.getLogger(__name__)


# ============================================================
# HOME CARE REQUEST
# ============================================================

def request_home_care(request):

    if request.method == "POST":

        form = HomeCareRequestForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            homecare_request = form.save()

            custom_services = form.cleaned_data.get(
                "custom_services"
            )

            if custom_services:
                homecare_request.description += (
                    f"\n\n[Custom Requested Services]: "
                    f"{custom_services}"
                )

                homecare_request.save(
                    update_fields=["description"]
                )

            files = request.FILES.getlist(
                "attachments"
            )

            for f in files:

                HomeCareRequestAttachment.objects.create(
                    homecare_request=homecare_request,
                    file=f,
                )

            request.session["homecare_reference"] = (
                homecare_request.id
            )

            messages.success(
                request,
                "Thank you. Your home care request has been received. "
                "Our team will contact you shortly.",
            )

            return redirect(
                "homecare:success"
            )

    else:

        form = HomeCareRequestForm()

    return render(
        request,
        "homecare/request.html",
        {
            "form": form,
        },
    )


def request_success(request):

    reference = request.session.get(
        "homecare_reference"
    )

    return render(
        request,
        "homecare/success.html",
        {
            "reference": reference,
        },
    )


# ============================================================
# REFERRAL
# ============================================================
def refer_a_patient(request):

    if request.method == "POST":

        referral_form = ReferralForm(
            request.POST,
            request.FILES,
        )

        homecare_form = HomeCareRequestForm(
            request.POST,
            request.FILES,
        )

        if referral_form.is_valid() and homecare_form.is_valid():

            with transaction.atomic():

                # ------------------------------------------------
                # SAVE REFERRER DETAILS
                # ------------------------------------------------

                referral = referral_form.save()

                # ------------------------------------------------
                # SAVE PATIENT USING NORMAL HOME CARE FORM
                # ------------------------------------------------

                homecare_request = homecare_form.save()

                # ------------------------------------------------
                # ADD REFERRER INFORMATION TO HOME CARE REQUEST
                # ------------------------------------------------

                facility_name = (
                    referral.referring_facility.strip()
                    if referral.referring_facility
                    else ""
                )

                facility_info = (
                    f" ({facility_name})"
                    if facility_name
                    else ""
                )

                referral_information = (
                    f"\n\n"
                    f"[REFERRAL INFORMATION]\n"
                    f"Referred by: {referral.referrer_name}"
                    f"{facility_info}\n"
                    f"Referrer Email: {referral.referrer_email}\n"
                    f"Referrer Phone: {referral.referrer_phone}"
                )

                if homecare_request.description:
                    homecare_request.description += (
                        referral_information
                    )
                else:
                    homecare_request.description = (
                        referral_information
                    )

                homecare_request.save(
                    update_fields=["description"]
                )

                # ------------------------------------------------
                # COPY ATTACHMENTS TO HOME CARE REQUEST
                # ------------------------------------------------

                files = request.FILES.getlist(
                    "attachments"
                )

                for f in files:

                    ReferralAttachment.objects.create(
                        referral=referral,
                        file=f,
                    )

                    HomeCareRequestAttachment.objects.create(
                        homecare_request=homecare_request,
                        file=f,
                    )

                # ------------------------------------------------
                # LINK REFERRAL TO HOME CARE REQUEST
                # ------------------------------------------------

                referral.homecare_request = (
                    homecare_request
                )

                referral.save(
                    update_fields=[
                        "homecare_request"
                    ]
                )

            messages.success(
                request,
                "Thank you! Your referral has been submitted. "
                "Our care team will review the patient details "
                "and contact the patient with a quotation.",
            )

            return redirect(
                "homecare:referral_success"
            )

    else:

        referral_form = ReferralForm()

        homecare_form = HomeCareRequestForm()

    return render(
        request,
        "homecare/referral_form.html",
        {
            "referral_form": referral_form,
            "homecare_form": homecare_form,
        },
    )
    
def referral_success(request):

    return render(
        request,
        "homecare/referral_success.html",
    )


# ============================================================
# BOOK APPOINTMENT / CONSULTATION
# ============================================================

@require_http_methods(["GET", "POST"])
def book_appointment(request):

    if request.method == "GET":

        return redirect(
            "home"
        )

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    phone = request.POST.get("phone", "").strip()
    services = request.POST.getlist("services")
    appointment_date_value = request.POST.get("appointment_date", "").strip()
    appointment_time_value = request.POST.get("appointment_time", "").strip()
    message = request.POST.get("message", "").strip()

    errors = []

    if not first_name:
        errors.append("First name is required.")

    if not last_name:
        errors.append("Last name is required.")

    if not email:
        errors.append("Email address is required.")

    if not phone:
        errors.append("Phone number is required.")

    if not appointment_date_value:
        errors.append("Appointment date is required.")

    if not appointment_time_value:
        errors.append("Appointment time is required.")

    appointment_date = None
    appointment_time = None

    if appointment_date_value:
        try:
            appointment_date = datetime.strptime(
                appointment_date_value,
                "%Y-%m-%d",
            ).date()

            if appointment_date < timezone.now().date():
                errors.append("Appointment date cannot be in the past.")

        except ValueError:
            errors.append("Please enter a valid appointment date.")

    if appointment_time_value:
        try:
            appointment_time = datetime.strptime(
                appointment_time_value,
                "%H:%M",
            ).time()

        except ValueError:
            errors.append("Please enter a valid appointment time.")

    if errors:
        request.session["appointment_errors"] = errors
        request.session["appointment_form_data"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "services": services,
            "appointment_date": appointment_date_value,
            "appointment_time": appointment_time_value,
            "message": message,
        }
        return redirect("home")

    with transaction.atomic():
        consultation = Consultation(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            services=services,
            requested_date=appointment_date,
            requested_time=appointment_time,
            message=message,
            status=Consultation.Status.PENDING,
        )

        consultation.full_clean()
        consultation.save()

        uploaded_files = request.FILES.getlist("attachments")

        for uploaded_file in uploaded_files:
            ConsultationAttachment.objects.create(
                consultation=consultation,
                file=uploaded_file,
            )

    request.session["consultation_reference"] = consultation.id

    messages.success(
        request,
        "Your appointment request has been received. "
        "Our team will review it and prepare your quotation.",
    )

    return redirect("homecare:appointment_success")


def appointment_success(request):

    reference = request.session.get(
        "consultation_reference"
    )

    return render(
        request,
        "homecare/appointment_success.html",
        {
            "reference": reference,
        },
    )



# ============================================================
# HOME CARE QUOTATION
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def create_quotation(
    request,
    request_id,
):

    homecare_request = get_object_or_404(
        HomeCareRequest.objects
        .prefetch_related("services"),
        id=request_id,
    )

    # --------------------------------------------------------
    # PREVENT DUPLICATE QUOTATIONS
    # --------------------------------------------------------

    if hasattr(
        homecare_request,
        "quotation",
    ):

        messages.warning(
            request,
            "A quotation already exists for this request.",
        )

        return redirect(
            "admin:homecare_homecarerequest_change",
            homecare_request.id,
        )

    # --------------------------------------------------------
    # CREATE UNSAVED QUOTATION
    # --------------------------------------------------------

    quotation_instance = Quotation(
        homecare_request=homecare_request
    )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = QuotationForm(
            request.POST,
            instance=quotation_instance,
        )

        # We cannot save an inline formset until the
        # quotation itself exists.
        #
        # Validate quotation form first.
        if form.is_valid():

            try:

                with transaction.atomic():

                    # ----------------------------------------
                    # SAVE QUOTATION
                    # ----------------------------------------

                    quotation = form.save(
                        commit=False
                    )

                    quotation.homecare_request = (
                        homecare_request
                    )

                    quotation.payment_status = (
                        Quotation.PaymentStatus.PENDING
                    )

                    now = timezone.now()

                    quotation.sent_at = now

                    quotation.payment_deadline = (
                        now + timedelta(hours=24)
                    )

                    # Initial values.
                    quotation.base_amount = Decimal("0.00")
                    quotation.amount = Decimal("0.00")

                    quotation.save()

                    # ----------------------------------------
                    # SAVE LINE ITEMS
                    # ----------------------------------------

                    item_formset = QuotationItemFormSet(
                        request.POST,
                        instance=quotation,
                    )

                    if not item_formset.is_valid():

                        # Roll back the quotation.
                        raise ValueError(
                            "Please correct the quotation items."
                        )

                    items = item_formset.save(
                        commit=False
                    )

                    # ----------------------------------------
                    # SAVE / DELETE ITEMS
                    # ----------------------------------------

                    for item in items:

                        # Existing service.
                        if item.service:

                            # If staff leaves name blank,
                            # use the actual database service name.
                            if not item.name.strip():
                                item.name = (
                                    item.service.name
                                )

                        # Custom service.
                        else:

                            item.name = (
                                item.name or ""
                            ).strip()

                            if not item.name:

                                raise ValueError(
                                    "Every custom service "
                                    "must have a name."
                                )

                        # Server-side line total.
                        item.line_total = (
                            item.calculate_total()
                        )

                        item.save()

                    # Delete rows marked for deletion.
                    for item in item_formset.deleted_objects:

                        item.delete()

                    # ----------------------------------------
                    # SECURE SERVER-SIDE TOTAL
                    # ----------------------------------------

                    quotation.base_amount = (
                        quotation.calculate_items_total()
                    )

                    quotation.amount = (
                        quotation.calculate_total()
                    )

                    quotation.save(
                        update_fields=[
                            "base_amount",
                            "amount",
                            "updated_at",
                        ]
                    )

                    # ----------------------------------------
                    # UPDATE HOME CARE REQUEST
                    # ----------------------------------------

                    homecare_request.status = (
                        HomeCareRequest.Status.PAYMENT_PENDING
                    )

                    homecare_request.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

                # ------------------------------------------------
                # BUILD SECURE QUOTATION URL
                # ------------------------------------------------

                quotation_url = request.build_absolute_uri(
                    reverse(
                        "homecare:quotation_detail",
                        kwargs={
                            "token": quotation.access_token
                        },
                    )
                )

                # ------------------------------------------------
                # SEND EMAIL
                # ------------------------------------------------

                try:

                    send_quotation_email(
                        quotation,
                        quotation_url,
                    )

                    messages.success(
                        request,
                        (
                            "Quotation saved and sent "
                            "successfully to the client."
                        ),
                    )

                except Exception as e:

                    logger.exception(
                        "Failed to send quotation email."
                    )

                    messages.warning(
                        request,
                        (
                            "Quotation was saved successfully, "
                            "but the email could not be sent. "
                            f"Error: {e}"
                        ),
                    )

                return redirect(
                    "admin:homecare_homecarerequest_change",
                    homecare_request.id,
                )

            except ValueError as e:

                messages.error(
                    request,
                    str(e),
                )

        # ----------------------------------------------------
        # FORM INVALID
        # ----------------------------------------------------

        item_formset = QuotationItemFormSet(
            request.POST,
            instance=quotation_instance,
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    else:

        form = QuotationForm(
            instance=quotation_instance,
        )

        # Existing requested services become the initial
        # quotation lines.
        initial_items = []

        for service in homecare_request.services.all():

            initial_items.append(
                {
                    "service": service.pk,
                    "name": service.name,
                    "quantity": Decimal("1.00"),
                    "unit_price": service.price,
                    "description": "",
                }
            )

        item_formset = QuotationItemFormSet(
            instance=quotation_instance,
            initial=initial_items,
        )

    # --------------------------------------------------------
    # DISPLAY TOTAL
    # --------------------------------------------------------

    return render(
        request,
        "homecare/quotation_form.html",
        {
            "form": form,
            "item_formset": item_formset,
            "homecare_request": homecare_request,
            "calculated_total": (
                sum(
                    (
                        service.price
                        for service
                        in homecare_request.services.all()
                    ),
                    Decimal("0.00"),
                )
            ),
            "is_consultation": False,
        },
    )


def send_quotation_email(
    quotation,
    quotation_url,
):

    homecare_request = quotation.homecare_request
    site_settings = SiteSettings.load()
    local_deadline = timezone.localtime(quotation.payment_deadline)

    subject = "Your Home Care Quotation - Hands-On Health"

    context = {
        "quotation": quotation,
        "homecare_request": homecare_request,
        "quotation_url": quotation_url,
        "payment_deadline": local_deadline,
        "site_settings": site_settings,
    }

    html_content = render_to_string(
        "homecare/email/quotation_email.html",
        context,
    )

    services = homecare_request.services.all()

    if services.exists():
        service_name = ", ".join(
            getattr(service, "title", getattr(service, "name", "Home Care Service"))
            for service in services
        )
    else:
        service_name = "Home Care Service"

    text_content = f"""
Dear {homecare_request.full_name},

Thank you for contacting Hands-On Health.

We have reviewed your home care request and prepared your quotation.

Service(s):
{service_name}

Location:
{homecare_request.location}

Quotation Amount:
N$ {quotation.amount:,.2f}

Payment Deadline:
{local_deadline.strftime("%d %B %Y at %I:%M %p")}

QUOTATION DETAILS
-----------------
{quotation.description}

PAYMENT INFORMATION
-------------------

Bank:
{site_settings.bank_name or "Please refer to the quotation page."}

Account Name:
{site_settings.account_name or "Please refer to the quotation page."}

Account Number:
{site_settings.account_number or "Please refer to the quotation page."}

Branch:
{site_settings.branch_name or "Please refer to the quotation page."}

Mobile Money:
{site_settings.mobile_money_name or "Please refer to the quotation page."}

Mobile Money Number:
{site_settings.mobile_money_number or "Please refer to the quotation page."}

{site_settings.payment_instructions or ""}

Review your quotation and payment information using the secure link below:

{quotation_url}

Please note that your service is not confirmed until payment has been received and verified by Hands-On Health.

Phone: {site_settings.phone or "Not provided"}
WhatsApp: {site_settings.whatsapp or "Not provided"}
Email: {site_settings.email or "Not provided"}

Kind regards,

{site_settings.business_name}
{site_settings.tagline or "Home-Based Healthcare Services"}
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[homecare_request.email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send()


# ============================================================
# CONSULTATION QUOTATION
# ============================================================

@login_required
def create_consultation_quotation(
    request,
    consultation_id,
):

    if not _user_is_admin_or_superuser(request.user):
        raise Http404

    consultation = get_object_or_404(
        Consultation,
        pk=consultation_id,
    )

    if hasattr(consultation, "quotation"):
        messages.warning(
            request,
            "A quotation already exists for this consultation.",
        )
        return redirect(
            "admin:homecare_consultation_change",
            consultation.id,
        )

    quotation_instance = Quotation(consultation=consultation)

    if request.method == "POST":
        form = QuotationForm(
            request.POST,
            instance=quotation_instance,
        )

        if form.is_valid():
            quotation = form.save(commit=False)
            now = timezone.now()

            quotation.sent_at = now
            quotation.payment_deadline = now + timedelta(hours=24)
            quotation.payment_status = Quotation.PaymentStatus.PENDING
            quotation.save()

            consultation.status = Consultation.Status.PAYMENT_PENDING
            consultation.save(update_fields=["status", "updated_at"])

            quotation_url = request.build_absolute_uri(
                reverse(
                    "homecare:quotation_detail",
                    kwargs={"token": quotation.access_token},
                )
            )

            try:
                send_consultation_quotation_email(quotation, quotation_url)
                messages.success(
                    request,
                    "Consultation quotation created and sent to the patient.",
                )
            except Exception as e:
                logger.exception("Consultation quotation email failed.")
                messages.warning(
                    request,
                    f"Quotation was created, but email failed: {e}",
                )

            return redirect(
                "admin:homecare_consultation_change",
                consultation.id,
            )

    else:
        form = QuotationForm(
            instance=quotation_instance,
            initial={
                "base_amount": 0,
                "transportation_fee": 0,
                "discount_amount": 0,
                "amount": 0,
                "description": (
                    "Consultation Services:\n"
                    f"{consultation.services or 'Consultation'}"
                ),
            },
        )

    return render(
        request,
        "homecare/quotation_form.html",
        {
            "form": form,
            "consultation": consultation,
            "is_consultation": True,
        },
    )


def send_consultation_quotation_email(
    quotation,
    quotation_url,
):

    consultation = quotation.consultation
    site_settings = SiteSettings.load()
    local_deadline = timezone.localtime(quotation.payment_deadline)

    services = consultation.services or []

    if isinstance(services, list):
        service_text = ", ".join(str(service) for service in services)
    else:
        service_text = str(services)

    subject = "Your Consultation Quotation - Hands-On Health"

    text_content = f"""
Dear {consultation.first_name} {consultation.last_name},

Thank you for booking a consultation with Hands-On Health.

We have reviewed your appointment request and prepared your quotation.

Consultation Services:
{service_text or "Medical Consultation"}

Requested Date:
{consultation.requested_date}

Requested Time:
{consultation.requested_time}

Quotation Amount:
N$ {quotation.amount:,.2f}

Payment Deadline:
{local_deadline.strftime("%d %B %Y at %I:%M %p")}

QUOTATION DETAILS
-----------------
{quotation.description}

You can review your quotation and submit payment using the secure link below:

{quotation_url}

IMPORTANT
---------
Your consultation is not scheduled until:

1. Payment has been submitted.
2. Payment has been verified.
3. Hands-On Health shares available appointment slots with you.
4. You select one of the available slots.

Once you select a slot, your consultation will be confirmed and your telemedicine link will be provided.

If you have any questions, please contact:

Phone:
{site_settings.phone or "Not provided"}

WhatsApp:
{site_settings.whatsapp or "Not provided"}

Email:
{site_settings.email or "Not provided"}

Kind regards,

{site_settings.business_name}
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[consultation.email],
    )

    email.send()


# ============================================================
# CAREGIVER DASHBOARD
# ============================================================

@login_required
def caregiver_dashboard(
    request,
    token,
):

    try:
        assignment_id = signing.TimestampSigner().unsign(
            token,
            max_age=60 * 60 * 24 * 7,
        )

    except signing.BadSignature:
        messages.error(
            request,
            "This caregiver dashboard link is invalid or has expired.",
        )

        return render(
            request,
            "homecare/caregiver_link_expired.html",
            {
                "message": (
                    "This caregiver dashboard link is invalid "
                    "or has expired."
                ),
            },
        )

    assignment = get_object_or_404(
        CaregiverAssignment.objects
        .select_related(
            "caregiver",
            "homecare_request",
        )
        .prefetch_related(
            "homecare_request__services"
        ),
        id=assignment_id,
    )

    if not assignment.caregiver.is_active:
        return render(
            request,
            "homecare/caregiver_link_expired.html",
            {
                "message": (
                    "This caregiver account is currently inactive."
                ),
            },
        )

    return render(
        request,
        "homecare/caregiver_dashboard.html",
        {
            "assignment": assignment,
        },
    )


def send_caregiver_assignment_email(
    assignment,
    base_url=None,
):
    """
    Send the caregiver assignment email.

    Supports BOTH calling styles used by older/newer staff views:

        send_caregiver_assignment_email(assignment, base_url)

    and:

        send_caregiver_assignment_email(request, assignment)

    The actual email mechanism remains the proven
    EmailMultiAlternatives + email.send() implementation.
    """

    # --------------------------------------------------------
    # SUPPORT BOTH OLD AND NEW CALLING STYLES
    # --------------------------------------------------------

    request_object = None

    if isinstance(assignment, CaregiverAssignment):
        actual_assignment = assignment
        actual_base_url = base_url
    else:
        # Newer staff view may call:
        # send_caregiver_assignment_email(request, assignment)
        request_object = assignment
        actual_assignment = base_url
        actual_base_url = None

    assignment = actual_assignment

    if assignment is None:
        raise ValueError(
            "Caregiver assignment was not supplied."
        )

    caregiver = assignment.caregiver
    homecare_request = assignment.homecare_request

    # --------------------------------------------------------
    # CAREGIVER EMAIL
    # --------------------------------------------------------

    if not caregiver.email:
        logger.error(
            "Caregiver assignment #%s has no caregiver email address.",
            assignment.id,
        )
        raise ValueError(
            "The assigned caregiver does not have an email address."
        )

    # --------------------------------------------------------
    # SITE SETTINGS
    # --------------------------------------------------------

    site_settings = SiteSettings.load()

    # --------------------------------------------------------
    # BUILD CURRENT ASSIGNMENT URL
    # --------------------------------------------------------
    # The current caregiver portal uses:
    # /caregiver/assignments/<assignment-id>/
    #
    # Keep the old signed-token dashboard as a fallback so existing
    # deployments/templates do not suddenly break if the named URL
    # is unavailable.

    try:
        assignment_path = reverse(
            "caregivers:assignment_detail",
            kwargs={"pk": assignment.pk},
        )

        if request_object is not None and hasattr(
            request_object,
            "build_absolute_uri",
        ):
            dashboard_url = request_object.build_absolute_uri(
                assignment_path
            )
        else:
            actual_base_url = (
                actual_base_url
                or getattr(settings, "SITE_URL", "")
                or "http://127.0.0.1:8000"
            ).rstrip("/")

            dashboard_url = (
                f"{actual_base_url}{assignment_path}"
            )

    except Exception:
        logger.exception(
            "Could not build caregiver assignment detail URL."
        )

        # Legacy signed-token URL fallback.
        token = signing.TimestampSigner().sign(
            str(assignment.id)
        )

        if request_object is not None and hasattr(
            request_object,
            "build_absolute_uri",
        ):
            dashboard_url = request_object.build_absolute_uri(
                f"/caregiver/dashboard/{token}/"
            )
        else:
            actual_base_url = (
                actual_base_url
                or getattr(settings, "SITE_URL", "")
                or "http://127.0.0.1:8000"
            ).rstrip("/")

            dashboard_url = (
                f"{actual_base_url}/caregiver/dashboard/{token}/"
            )

    # --------------------------------------------------------
    # SAFE DATE / TIME DISPLAY
    # --------------------------------------------------------

    service_date = getattr(
        assignment,
        "service_date",
        None,
    ) or getattr(
        assignment,
        "start_date",
        None,
    )

    service_time = getattr(
        assignment,
        "service_time",
        None,
    )

    if service_date:
        service_date_text = service_date.strftime(
            "%d %B %Y"
        )
    else:
        service_date_text = "To be confirmed"

    if service_time:
        service_time_text = service_time.strftime(
            "%I:%M %p"
        )
    else:
        service_time_text = "To be confirmed"

    # --------------------------------------------------------
    # HTML EMAIL
    # --------------------------------------------------------

    context = {
        "assignment": assignment,
        "caregiver": caregiver,
        "homecare_request": homecare_request,
        "dashboard_url": dashboard_url,
        "site_settings": site_settings,
    }

    html_content = render_to_string(
        "homecare/email/caregiver_assignment.html",
        context,
    )

    # --------------------------------------------------------
    # PLAIN TEXT EMAIL
    # --------------------------------------------------------

    caregiver_name = getattr(
        caregiver,
        "name",
        "Caregiver",
    ) or "Caregiver"

    text_content = f"""
Dear {caregiver_name},

You have been assigned a new home care patient by Hands-On Health.

PATIENT DETAILS
---------------

Patient:
{homecare_request.full_name}

Phone:
{getattr(homecare_request, 'phone', '') or 'Not provided'}

Email:
{getattr(homecare_request, 'email', '') or 'Not provided'}

Location:
{getattr(homecare_request, 'location', '') or 'To be confirmed'}

Service Date:
{service_date_text}

Service Time:
{service_time_text}

Assignment Status:
Pending Acceptance

Please use the secure link below to review the assignment and accept or decline it:

{dashboard_url}

If you accept the assignment, you will be able to start the assignment and submit the required daily reports through your caregiver dashboard.

If you decline the assignment, the administrator will be notified and may assign another caregiver.

Kind regards,

{site_settings.business_name}
{site_settings.phone or ''}
{site_settings.email or ''}
"""

    # --------------------------------------------------------
    # SEND EMAIL
    # --------------------------------------------------------

    email = EmailMultiAlternatives(
        subject=(
            "New Patient Assigned to You — "
            f"{homecare_request.full_name}"
        ),
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[caregiver.email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    # IMPORTANT: fail_silently=False so staff receives the actual
    # SMTP/template error instead of believing the email was sent.
    email.send(
        fail_silently=False
    )

    logger.info(
        "Caregiver assignment email sent successfully. "
        "Assignment #%s -> %s",
        assignment.id,
        caregiver.email,
    )


# ============================================================
# QUOTATION DETAIL
# ============================================================

def quotation_detail(
    request,
    token,
):

    quotation = get_object_or_404(
        Quotation.objects.select_related(
            "homecare_request",
            "consultation",
        ),
        access_token=token,
    )

    site_settings = SiteSettings.load()

    local_deadline = None

    if quotation.payment_deadline:
        local_deadline = timezone.localtime(
            quotation.payment_deadline
        )

    return render(
        request,
        "homecare/quotation_detail.html",
        {
            "quotation": quotation,
            "homecare_request": quotation.homecare_request,
            "consultation": quotation.consultation,
            "site_settings": site_settings,
            "payment_deadline": local_deadline,
        },
    )


# ============================================================
# PAYMENT PLACEHOLDER
# ============================================================

def payment_placeholder(
    request,
    token,
):

    quotation = get_object_or_404(
        Quotation.objects.select_related(
            "homecare_request",
            "consultation",
        ),
        access_token=token,
    )

    return render(
        request,
        "homecare/payment_placeholder.html",
        {
            "quotation": quotation,
            "homecare_request": quotation.homecare_request,
            "consultation": quotation.consultation,
        },
    )


# ============================================================
# SUBMIT PAYMENT
# ============================================================

def submit_payment(
    request,
    token,
):

    quotation = get_object_or_404(
        Quotation.objects.select_related(
            "homecare_request",
            "consultation",
        ),
        access_token=token,
    )

    homecare_request = quotation.homecare_request
    consultation = quotation.consultation

    if request.method == "POST":

        form = PaymentSubmissionForm(request.POST)

        if form.is_valid():

            payment = form.save(commit=False)
            payment.quotation = quotation
            payment.amount = quotation.amount
            payment.status = Payment.Status.PENDING
            payment.save()

            if homecare_request:
                homecare_request.status = HomeCareRequest.Status.PAYMENT_RECEIVED
                homecare_request.save(update_fields=["status", "updated_at"])

            elif consultation:
                consultation.status = Consultation.Status.PAYMENT_PENDING
                consultation.save(update_fields=["status", "updated_at"])

            messages.success(
                request,
                "Payment submitted successfully. "
                "Our team will verify your payment shortly.",
            )

            return redirect(
                "homecare:payment_submitted",
                token=quotation.access_token,
            )

    else:

        form = PaymentSubmissionForm()

    return render(
        request,
        "homecare/payment_form.html",
        {
            "quotation": quotation,
            "homecare_request": homecare_request,
            "consultation": consultation,
            "form": form,
        },
    )


# ============================================================
# PAYMENT SUBMITTED
# ============================================================

def payment_submitted(
    request,
    token,
):

    quotation = get_object_or_404(
        Quotation.objects.select_related(
            "homecare_request",
            "consultation",
        ),
        access_token=token,
    )

    return render(
        request,
        "homecare/payment_submitted.html",
        {
            "quotation": quotation,
            "homecare_request": quotation.homecare_request,
            "consultation": quotation.consultation,
        },
    )


# ============================================================
# VERIFY PAYMENT
# ============================================================

@login_required
def verify_payment(
    request,
    payment_id,
):

    next_url = request.POST.get("next") or request.GET.get("next")
    referer = request.META.get("HTTP_REFERER", "")

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        redirect_target = next_url
    elif "/staff/" in referer:
        try:
            redirect_target = reverse("staff:payments")
        except Exception:
            redirect_target = reverse("admin:homecare_payment_changelist")
    else:
        redirect_target = reverse("admin:homecare_payment_changelist")

    if request.method != "POST":
        messages.error(
            request,
            "Invalid payment verification request.",
        )
        return redirect(redirect_target)

    payment = get_object_or_404(
        Payment.objects.select_related(
            "quotation",
            "quotation__homecare_request",
            "quotation__consultation",
        ),
        id=payment_id,
    )

    if payment.status == Payment.Status.VERIFIED:
        messages.info(
            request,
            "This payment has already been verified.",
        )
        return redirect(redirect_target)

    if payment.status == Payment.Status.REJECTED:
        messages.error(
            request,
            "A rejected payment cannot be verified.",
        )
        return redirect(redirect_target)

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
        return redirect(redirect_target)

    # Handle VERIFY Action
    quotation = payment.quotation
    homecare_request = quotation.homecare_request
    consultation = quotation.consultation

    with transaction.atomic():
        payment.status = Payment.Status.VERIFIED
        payment.verified_at = now
        payment.verified_by = request.user
        payment.save(update_fields=["status", "verified_at", "verified_by"])

        quotation.payment_status = Quotation.PaymentStatus.PAID
        quotation.paid_at = now
        quotation.save(update_fields=["payment_status", "paid_at", "updated_at"])

        if homecare_request:
            homecare_request.status = HomeCareRequest.Status.CONFIRMED
            homecare_request.confirmed_at = now
            homecare_request.save(update_fields=["status", "confirmed_at", "updated_at"])
            transaction.on_commit(lambda: send_payment_confirmation_email(payment))
            messages.success(
                request,
                "Payment verified successfully. Home care request confirmed.",
            )

        elif consultation:
            consultation.status = Consultation.Status.PAID
            consultation.save(update_fields=["status", "updated_at"])
            transaction.on_commit(lambda: send_consultation_payment_confirmation_email(payment))
            messages.success(
                request,
                "Payment verified successfully. Consultation marked as PAID.",
            )

    return redirect(redirect_target)


# ============================================================
# HOME CARE PAYMENT CONFIRMATION EMAIL
# ============================================================

def send_payment_confirmation_email(
    payment,
):

    quotation = payment.quotation
    homecare_request = quotation.homecare_request
    site_settings = SiteSettings.load()

    subject = "Payment Confirmed — Hands-On Health"

    context = {
        "payment": payment,
        "quotation": quotation,
        "homecare_request": homecare_request,
        "site_settings": site_settings,
    }

    html_content = render_to_string(
        "homecare/email/payment_confirmation.html",
        context,
    )

    text_content = f"""
Dear {homecare_request.full_name},

Thank you for your payment.

Your payment has been successfully verified.

Quotation:
#{quotation.id}

Amount Paid:
N$ {payment.amount:,.2f}

Payment Method:
{payment.get_payment_method_display()}

Transaction Code:
{payment.payment_code}

Your home care request has now been confirmed.

Our team will contact you regarding the next steps.

Kind regards,

{site_settings.business_name}
{site_settings.phone}
{site_settings.email}
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[homecare_request.email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send()


# ============================================================
# CONSULTATION PAYMENT CONFIRMATION EMAIL
# ============================================================

def send_consultation_payment_confirmation_email(
    payment,
):

    quotation = payment.quotation
    consultation = quotation.consultation
    site_settings = SiteSettings.load()

    subject = "Consultation Payment Confirmed — Hands-On Health"

    text_content = f"""
Dear {consultation.first_name} {consultation.last_name},

Your consultation payment has been successfully verified.

Payment Details
---------------

Quotation:
#{quotation.id}

Amount Paid:
N$ {payment.amount:,.2f}

Payment Method:
{payment.get_payment_method_display()}

Transaction Code:
{payment.payment_code}

Your consultation is now ready for scheduling.

Our team will manually prepare available consultation
dates and times for you.

Once the available slots are ready, you will receive
an email containing a secure link where you can select
your preferred date and time.

Your consultation will only be scheduled after you
select one of the available slots.

Kind regards,

{site_settings.business_name}

Phone:
{site_settings.phone or "Not provided"}

WhatsApp:
{site_settings.whatsapp or "Not provided"}

Email:
{site_settings.email or "Not provided"}
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[consultation.email],
    )

    email.send()


# ============================================================
# ADMIN / DOCTOR HELPER
# ============================================================

def _user_is_admin_or_superuser(
    user
):

    return (
        user.is_superuser
        or user.is_staff
    )


# ============================================================
# MANAGE CONSULTATION SLOTS
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def schedule_consultation(
    request,
    consultation_id,
):

    if not _user_is_admin_or_superuser(request.user):
        raise Http404

    consultation = get_object_or_404(
        Consultation,
        pk=consultation_id,
    )

    if consultation.status != Consultation.Status.PAID:
        messages.error(
            request,
            (
                "Available appointment slots can only be "
                "created after payment has been verified."
            ),
        )
        return redirect(
            "admin:homecare_consultation_change",
            consultation.pk,
        )

    if request.method == "POST":
        date_value = request.POST.get("date", "").strip()
        time_value = request.POST.get("time", "").strip()
        duration_value = request.POST.get("duration_minutes", "30").strip()

        try:
            slot_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Please enter a valid appointment date.")
            return redirect("homecare:schedule_consultation", consultation.pk)

        try:
            slot_time = datetime.strptime(time_value, "%H:%M").time()
        except ValueError:
            messages.error(request, "Please enter a valid appointment time.")
            return redirect("homecare:schedule_consultation", consultation.pk)

        current_date = timezone.localdate()

        if slot_date < current_date:
            messages.error(request, "You cannot create an appointment slot in the past.")
            return redirect("homecare:schedule_consultation", consultation.pk)

        if slot_date == current_date:
            current_time = timezone.localtime().time()
            if slot_time <= current_time:
                messages.error(
                    request,
                    "You cannot create an appointment slot for a time that has already passed.",
                )
                return redirect("homecare:schedule_consultation", consultation.pk)

        try:
            duration = int(duration_value)
            if duration <= 0 or duration > 240:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(
                request,
                "Please enter a valid consultation duration between 1 and 240 minutes.",
            )
            return redirect("homecare:schedule_consultation", consultation.pk)

        existing_slot = ConsultationSlot.objects.filter(
            consultation=consultation,
            date=slot_date,
            time=slot_time,
        ).first()

        if existing_slot:
            messages.warning(request, "This appointment slot already exists.")
            return redirect("homecare:schedule_consultation", consultation.pk)

        ConsultationSlot.objects.create(
            consultation=consultation,
            date=slot_date,
            time=slot_time,
            duration_minutes=duration,
            is_available=True,
            is_selected=False,
        )

        messages.success(
            request,
            (
                f"Appointment slot {slot_date.strftime('%d %B %Y')} at "
                f"{slot_time.strftime('%I:%M %p')} was added successfully."
            ),
        )

        return redirect("homecare:schedule_consultation", consultation.pk)

    slots = ConsultationSlot.objects.filter(
        consultation=consultation
    ).order_by("date", "time")

    available_slots = slots.filter(
        is_available=True,
        is_selected=False,
    )

    return render(
        request,
        "homecare/schedule_consultation.html",
        {
            "consultation": consultation,
            "slots": slots,
            "available_slots": available_slots,
        },
    )


# ============================================================
# DELETE / REMOVE AVAILABLE SLOT
# ============================================================

@login_required
@require_http_methods(["POST"])
def delete_consultation_slot(
    request,
    slot_id,
):

    if not _user_is_admin_or_superuser(request.user):
        raise Http404

    slot = get_object_or_404(
        ConsultationSlot.objects.select_related("consultation"),
        pk=slot_id,
    )

    consultation = slot.consultation

    if slot.is_selected:
        messages.error(request, "A selected appointment slot cannot be deleted.")
        return redirect("homecare:schedule_consultation", consultation.pk)

    slot.delete()

    messages.success(request, "Appointment slot removed successfully.")

    return redirect("homecare:schedule_consultation", consultation.pk)


# ============================================================
# SEND CONSULTATION AVAILABILITY
# ============================================================

@login_required
@require_http_methods(["POST"])
def send_consultation_availability(
    request,
    consultation_id,
):

    if not _user_is_admin_or_superuser(request.user):
        raise Http404

    consultation = get_object_or_404(
        Consultation,
        pk=consultation_id,
    )

    if consultation.status != Consultation.Status.PAID:
        messages.error(
            request,
            "Availability can only be sent after payment is verified.",
        )
        return redirect(
            "admin:homecare_consultation_change",
            consultation.pk,
        )

    available_slots = ConsultationSlot.objects.filter(
        consultation=consultation,
        is_available=True,
        is_selected=False,
    ).order_by("date", "time")

    if not available_slots.exists():
        messages.error(
            request,
            "No available appointment slots have been created.",
        )
        return redirect("homecare:schedule_consultation", consultation.pk)

    try:
        send_consultation_availability_email(consultation)
        messages.success(
            request,
            "Available appointment slots have been sent to the patient.",
        )
    except Exception as e:
        logger.exception("Failed to send consultation availability.")
        messages.error(
            request,
            f"Unable to send availability email: {e}",
        )

    return redirect("homecare:schedule_consultation", consultation.pk)


# ============================================================
# PATIENT APPOINTMENT AVAILABILITY
# ============================================================

@require_http_methods(["GET"])
def consultation_availability(
    request,
    token,
):

    consultation = get_object_or_404(
        Consultation,
        booking_token=token,
    )

    if consultation.status not in (
        Consultation.Status.PAID,
        Consultation.Status.SCHEDULED,
    ):
        return render(
            request,
            "homecare/consultation_unavailable.html",
            {
                "consultation": consultation,
                "message": (
                    "Appointment scheduling is not currently "
                    "available for this consultation."
                ),
            },
        )

    if consultation.status == Consultation.Status.SCHEDULED:
        return render(
            request,
            "homecare/consultation_already_scheduled.html",
            {
                "consultation": consultation,
            },
        )

    slots = ConsultationSlot.objects.filter(
        consultation=consultation,
        is_available=True,
        is_selected=False,
    ).order_by("date", "time")

    return render(
        request,
        "homecare/consultation_availability.html",
        {
            "consultation": consultation,
            "slots": slots,
        },
    )


# ============================================================
# PATIENT SELECTS APPOINTMENT SLOT
# ============================================================

@require_http_methods(["POST"])
def select_consultation_slot(
    request,
    token,
    slot_id,
):

    with transaction.atomic():
        consultation = get_object_or_404(
            Consultation.objects.select_for_update(),
            booking_token=token,
        )

        if consultation.status != Consultation.Status.PAID:
            messages.error(
                request,
                "This consultation is not currently available for scheduling.",
            )
            return redirect(
                "homecare:consultation_availability",
                token=token,
            )

        slot = get_object_or_404(
            ConsultationSlot.objects.select_for_update(),
            pk=slot_id,
            consultation=consultation,
        )

        if not slot.is_available:
            messages.error(
                request,
                "This appointment slot is no longer available.",
            )
            return redirect(
                "homecare:consultation_availability",
                token=token,
            )

        if slot.is_selected:
            messages.error(
                request,
                "This appointment slot has already been selected.",
            )
            return redirect(
                "homecare:consultation_availability",
                token=token,
            )

        slot.is_selected = True
        slot.is_available = False
        slot.selected_at = timezone.now()
        slot.save(
            update_fields=[
                "is_selected",
                "is_available",
                "selected_at",
                "updated_at",
            ]
        )

        ConsultationSlot.objects.filter(
            consultation=consultation,
        ).exclude(pk=slot.pk).update(
            is_available=False,
            updated_at=timezone.now(),
        )

        consultation.consultation_date = slot.date
        consultation.consultation_time = slot.time
        consultation.duration_minutes = slot.duration_minutes
        consultation.status = Consultation.Status.SCHEDULED

        patient_url = request.build_absolute_uri(
            reverse(
                "homecare:patient_telemedicine",
                kwargs={"token": consultation.patient_access_token},
            )
        )

        doctor_url = request.build_absolute_uri(
            reverse(
                "homecare:doctor_telemedicine",
                kwargs={"token": consultation.doctor_access_token},
            )
        )

        consultation.patient_join_url = patient_url
        consultation.doctor_join_url = doctor_url
        consultation.save()

        transaction.on_commit(
            lambda: send_consultation_scheduled_email(consultation)
        )

    return redirect(
        "homecare:consultation_scheduled",
        token=consultation.booking_token,
    )


# ============================================================
# APPOINTMENT SCHEDULED SUCCESS PAGE
# ============================================================

def consultation_scheduled(
    request,
    token,
):

    consultation = get_object_or_404(
        Consultation,
        booking_token=token,
        status=Consultation.Status.SCHEDULED,
    )

    return render(
        request,
        "homecare/consultation_scheduled.html",
        {
            "consultation": consultation,
        },
    )


# ============================================================
# CONSULTATION AVAILABILITY EMAIL
# ============================================================

def send_consultation_availability_email(
    consultation,
    base_url=None,
):

    if not consultation.email:
        logger.warning(
            "Consultation #%s has no patient email.",
            consultation.id,
        )
        return

    available_slots = ConsultationSlot.objects.filter(
        consultation=consultation,
        is_available=True,
        is_selected=False,
    ).order_by("date", "time")

    if not available_slots.exists():
        logger.warning(
            "Consultation #%s has no available slots.",
            consultation.id,
        )
        return

    site_settings = SiteSettings.load()

    if not base_url:
        base_url = getattr(settings, "SITE_URL", "")

    base_url = (base_url or "").rstrip("/")

    if not base_url:
        base_url = "http://127.0.0.1:8000"

    availability_path = reverse(
        "homecare:consultation_availability",
        kwargs={"token": consultation.booking_token},
    )

    availability_url = f"{base_url}{availability_path}"

    slot_lines = []
    for slot in available_slots:
        slot_lines.append(
            f"- {slot.date.strftime('%A, %d %B %Y')} "
            f"at {slot.time.strftime('%I:%M %p')} "
            f"({slot.duration_minutes} minutes)"
        )

    slots_text = "\n".join(slot_lines)

    subject = "Choose Your Consultation Time - Hands-On Health"

    text_content = f"""
Dear {consultation.first_name} {consultation.last_name},

Your consultation payment has been verified and your appointment is now ready to be scheduled.

We have prepared the following available appointment times:

AVAILABLE APPOINTMENT TIMES
---------------------------

{slots_text}

Please click the secure link below to choose ONE of the available appointment times:

{availability_url}

IMPORTANT
---------

Only one appointment slot can be selected.

Once you select your preferred date and time:

- Your appointment will be confirmed.
- Your consultation status will change to SCHEDULED.
- Your secure telemedicine link will be provided.

Please do not share your appointment link with anyone else.

If you have any questions, please contact us.

Phone:
{site_settings.phone or "Not provided"}

WhatsApp:
{site_settings.whatsapp or "Not provided"}

Email:
{site_settings.email or "Not provided"}

Kind regards,

{site_settings.business_name}
{site_settings.tagline or "Healthcare Services"}
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[consultation.email],
    )

    email.send()


# ============================================================
# CONSULTATION SCHEDULED EMAIL
# ============================================================

def send_consultation_scheduled_email(
    consultation,
):

    if not consultation.email:
        return

    site_settings = SiteSettings.load()

    subject = "Consultation Confirmed - Hands-On Health"

    text_content = f"""
Dear {consultation.first_name} {consultation.last_name},

Your consultation has been successfully scheduled.

APPOINTMENT DETAILS
-------------------

Date:
{consultation.consultation_date.strftime("%A, %d %B %Y")}

Time:
{consultation.consultation_time.strftime("%I:%M %p")}

Duration:
{consultation.duration_minutes} minutes

Your consultation is now CONFIRMED.

PATIENT TELEMEDICINE LINK
-------------------------

{consultation.patient_join_url}

Please keep this link private and do not share it with anyone else.

You can use the link above at your scheduled appointment time.

Kind regards,

{site_settings.business_name}

Phone:
{site_settings.phone or "Not provided"}

WhatsApp:
{site_settings.whatsapp or "Not provided"}

Email:
{site_settings.email or "Not provided"}
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[consultation.email],
    )

    email.send()

    if consultation.doctor:
        doctor_email = getattr(consultation.doctor, "email", None)

        if doctor_email:
            doctor_name = (
                consultation.doctor.get_full_name()
                if hasattr(consultation.doctor, "get_full_name")
                else consultation.doctor.username
            )

            doctor_subject = "New Scheduled Telemedicine Consultation"

            doctor_text = f"""
Dear {doctor_name},

A consultation has been scheduled.

PATIENT
-------

Name:
{consultation.first_name} {consultation.last_name}

Date:
{consultation.consultation_date.strftime("%A, %d %B %Y")}

Time:
{consultation.consultation_time.strftime("%I:%M %p")}

Duration:
{consultation.duration_minutes} minutes

DOCTOR TELEMEDICINE LINK
------------------------

{consultation.doctor_join_url}

Please use the secure link above to join the consultation.

Kind regards,

{site_settings.business_name}
"""

            doctor_email_message = EmailMultiAlternatives(
                subject=doctor_subject,
                body=doctor_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[doctor_email],
            )

            doctor_email_message.send()


# ============================================================
# PATIENT TELEMEDICINE
# ============================================================

def _get_patient_consultation(token):
    consultation = get_object_or_404(
        Consultation,
        patient_access_token=token,
    )

    if consultation.status not in (
        Consultation.Status.SCHEDULED,
        Consultation.Status.IN_PROGRESS,
    ):
        raise Http404

    return consultation


def patient_telemedicine(
    request,
    token,
):

    consultation = _get_patient_consultation(token)

    return render(
        request,
        "homecare/telemedicine_patient.html",
        {
            "consultation": consultation,
            "patient": consultation,
            "room_name": consultation.room_name,
        },
    )


# ============================================================
# DOCTOR TELEMEDICINE
# ============================================================

def _get_doctor_consultation(token):
    consultation = get_object_or_404(
        Consultation,
        doctor_access_token=token,
    )

    if consultation.status not in (
        Consultation.Status.SCHEDULED,
        Consultation.Status.IN_PROGRESS,
    ):
        raise Http404

    return consultation


@login_required
def doctor_telemedicine(
    request,
    token,
):

    consultation = _get_doctor_consultation(token)

    if not _user_is_admin_or_superuser(request.user):
        raise Http404

    if (
        consultation.doctor_id
        and consultation.doctor_id != request.user.id
        and not request.user.is_superuser
    ):
        raise Http404

    return render(
        request,
        "homecare/telemedicine_doctor.html",
        {
            "consultation": consultation,
            "patient": consultation,
            "room_name": consultation.room_name,
        },
    )


# ============================================================
# START CONSULTATION
# ============================================================

@login_required
@require_http_methods(["POST"])
def start_consultation(
    request,
    consultation_id,
):

    if not _user_is_admin_or_superuser(request.user):
        raise Http404

    consultation = get_object_or_404(
        Consultation,
        pk=consultation_id,
    )

    if (
        consultation.doctor_id
        and consultation.doctor_id != request.user.id
        and not request.user.is_superuser
    ):
        raise Http404

    if consultation.status != Consultation.Status.SCHEDULED:
        messages.error(request, "This consultation cannot be started.")
        return redirect("admin:homecare_consultation_change", consultation.pk)

    consultation.status = Consultation.Status.IN_PROGRESS
    consultation.save(update_fields=["status", "updated_at"])

    return redirect(
        "homecare:doctor_telemedicine",
        token=consultation.doctor_access_token,
    )


# ============================================================
# COMPLETE CONSULTATION
# ============================================================

@login_required
@require_http_methods(["POST"])
def complete_consultation(
    request,
    consultation_id,
):

    if not _user_is_admin_or_superuser(request.user):
        raise Http404

    consultation = get_object_or_404(
        Consultation,
        pk=consultation_id,
    )

    if (
        consultation.doctor_id
        and consultation.doctor_id != request.user.id
        and not request.user.is_superuser
    ):
        raise Http404

    consultation.status = Consultation.Status.COMPLETED
    consultation.doctor_notes = request.POST.get("doctor_notes", "").strip()

    consultation.save(
        update_fields=[
            "status",
            "doctor_notes",
            "updated_at",
        ]
    )

    messages.success(request, "Consultation completed successfully.")

    return redirect("admin:homecare_consultation_change", consultation.pk)



# ============================================================
# CAREGIVER ASSIGNMENT WORKFLOW
# ============================================================
#
# Caregiver portal workflow:
#
#   PENDING ACCEPTANCE
#          |
#       ACCEPT
#          v
#       ACCEPTED
#          |
#       START
#          v
#     IN PROGRESS
#          |
#     DAILY REPORTS
#          |
#       COMPLETE
#          v
#      COMPLETED
#
# A caregiver may also DECLINE a pending assignment.
#
# IMPORTANT:
# - These views operate on CaregiverAssignment in homecare.models.
# - Daily reports remain in homecare.models.
# - Weekly reporting is presented as a weekly summary of the daily
#   reports, so this file does not require a second weekly-report
#   model to exist.
# - Access is restricted to the caregiver linked to request.user.
# ============================================================


def _caregiver_status(name, fallback=None):
    """
    Resolve a status from CaregiverAssignment.Status while remaining
    tolerant of the model being migrated between old and new status
    definitions.
    """
    status_class = getattr(CaregiverAssignment, "Status", None)
    if status_class is not None and hasattr(status_class, name):
        return getattr(status_class, name)
    return fallback


def _caregiver_assignment_queryset():
    """
    Common queryset used by caregiver portal pages.
    """
    return (
        CaregiverAssignment.objects
        .select_related(
            "caregiver",
            "caregiver__user",
            "homecare_request",
        )
        .prefetch_related(
            "homecare_request__services",
            "daily_reports",
        )
    )


def _get_logged_in_caregiver(request):
    """
    Return the caregiver profile belonging to the logged-in user.

    Caregivers must have an active portal account.
    """
    if not request.user.is_authenticated:
        raise Http404

    caregiver = getattr(request.user, "caregiver_profile", None)

    if caregiver is None:
        raise Http404

    if not caregiver.is_active:
        raise Http404

    return caregiver


def _get_caregiver_assignment(request, pk):
    """
    Securely retrieve an assignment belonging to the logged-in caregiver.
    """
    caregiver = _get_logged_in_caregiver(request)

    assignment = get_object_or_404(
        _caregiver_assignment_queryset(),
        pk=pk,
        caregiver=caregiver,
    )

    return caregiver, assignment


def _assignment_start_date(assignment):
    """
    Support the new start_date field while remaining compatible with
    older assignments that still have service_date.
    """
    return (
        getattr(assignment, "start_date", None)
        or getattr(assignment, "service_date", None)
    )


def _assignment_end_date(assignment):
    """
    Support the new end_date field while remaining compatible with
    older assignments.
    """
    return (
        getattr(assignment, "end_date", None)
        or getattr(assignment, "service_date", None)
        or _assignment_start_date(assignment)
    )


def _assignment_type_display(assignment):
    assignment_type = getattr(assignment, "assignment_type", None)

    if not assignment_type:
        return "One Day"

    try:
        return assignment.get_assignment_type_display()
    except Exception:
        value = str(assignment_type).upper()

        if "WEEK" in value:
            return "One Week"

        return "One Day"


def _assignment_status_label(assignment):
    try:
        return assignment.get_status_display()
    except Exception:
        return str(getattr(assignment, "status", "Unknown")).replace("_", " ").title()


def _set_homecare_assignment_status(homecare_request):
    """
    Reflect caregiver assignment progress on the HomeCareRequest where
    the corresponding status exists.
    """
    if not homecare_request:
        return

    try:
        if hasattr(HomeCareRequest.Status, "ASSIGNED"):
            homecare_request.status = HomeCareRequest.Status.ASSIGNED
            homecare_request.save(update_fields=["status", ])
    except Exception:
        logger.exception(
            "Unable to update HomeCareRequest assignment status."
        )


def _set_homecare_completed(homecare_request):
    """
    Mark the linked home-care request complete when the caregiver
    completes the assignment.
    """
    if not homecare_request:
        return

    try:
        if hasattr(HomeCareRequest.Status, "COMPLETED"):
            homecare_request.status = HomeCareRequest.Status.COMPLETED

            if hasattr(homecare_request, "completed_at"):
                homecare_request.completed_at = timezone.now()
                homecare_request.save(
                    update_fields=[
                        "status",
                        "completed_at",
                        
                    ]
                )
            else:
                homecare_request.save(
                    update_fields=[
                        "status",
                       
                    ]
                )
    except Exception:
        logger.exception(
            "Unable to update HomeCareRequest completion status."
        )


# ============================================================
# CAREGIVER PORTAL DASHBOARD
# ============================================================

@login_required
@require_http_methods(["GET"])
def caregiver_portal_dashboard(request):
    """
    Main authenticated caregiver dashboard.

    Assignment status values come directly from the actual
    CaregiverAssignment model:

        PENDING
        ACCEPTED
        IN_PROGRESS
        COMPLETED
        DECLINED
        CANCELLED
    """

    caregiver = _get_logged_in_caregiver(request)

    if caregiver is None:
        messages.error(
            request,
            "Your caregiver profile could not be found.",
        )
        return redirect("caregivers:login")

    assignments = (
        CaregiverAssignment.objects
        .filter(caregiver=caregiver)
        .select_related("homecare_request")
        .order_by("-assigned_at", "-id")
    )

    pending_assignments = assignments.filter(
        status=CaregiverAssignment.Status.PENDING
    )

    active_assignments = assignments.filter(
        status__in=[
            CaregiverAssignment.Status.ACCEPTED,
            CaregiverAssignment.Status.IN_PROGRESS,
        ]
    )

    completed_assignments = assignments.filter(
        status=CaregiverAssignment.Status.COMPLETED
    )

    declined_assignments = assignments.filter(
        status=CaregiverAssignment.Status.DECLINED
    )

    return render(
        request,
        "caregivers/dashboard.html",
        {
            "caregiver": caregiver,
            "assignments": assignments,
            "pending_assignments": pending_assignments,
            "active_assignments": active_assignments,
            "completed_assignments": completed_assignments,
            "declined_assignments": declined_assignments,

            "pending_count": pending_assignments.count(),
            "active_count": active_assignments.count(),
            "completed_count": completed_assignments.count(),
            "declined_count": declined_assignments.count(),
        },
    )


# ============================================================
# CAREGIVER ASSIGNMENTS
# ============================================================

@login_required
@require_http_methods(["GET"])
def caregiver_assignments(request):
    """
    List assignments belonging only to the logged-in caregiver.

    Supported filters:

        ?status=pending
        ?status=active
        ?status=completed
        ?status=declined
    """

    caregiver = _get_logged_in_caregiver(request)

    if caregiver is None:
        messages.error(
            request,
            "Your caregiver profile could not be found.",
        )
        return redirect("caregivers:login")

    assignments = (
        CaregiverAssignment.objects
        .filter(caregiver=caregiver)
        .select_related("homecare_request")
        .order_by("-assigned_at", "-id")
    )

    selected_status = (
        request.GET.get("status", "")
        .strip()
        .lower()
    )

    if selected_status == "pending":

        assignments = assignments.filter(
            status=CaregiverAssignment.Status.PENDING
        )

    elif selected_status == "active":

        assignments = assignments.filter(
            status__in=[
                CaregiverAssignment.Status.ACCEPTED,
                CaregiverAssignment.Status.IN_PROGRESS,
            ]
        )

    elif selected_status == "completed":

        assignments = assignments.filter(
            status=CaregiverAssignment.Status.COMPLETED
        )

    elif selected_status == "declined":

        assignments = assignments.filter(
            status=CaregiverAssignment.Status.DECLINED
        )

    return render(
        request,
        "caregivers/assignments.html",
        {
            "caregiver": caregiver,
            "assignments": assignments,
            "status_choices": CaregiverAssignment.Status.choices,
            "current_status": selected_status,
        },
    )


# ============================================================
# CAREGIVER ASSIGNMENT DETAIL
# ============================================================

@login_required
@require_http_methods(["GET"])
def caregiver_assignment_detail(request, pk):
    """
    Secure assignment detail page.

    A caregiver can only view their own assignments.
    """

    caregiver, assignment = _get_caregiver_assignment(
        request,
        pk,
    )

    reports = (
        assignment.daily_reports
        .all()
        .order_by(
            "-report_date",
            "-submitted_at",
        )
    )

    weekly_reports = (
        assignment.weekly_reports
        .all()
        .order_by(
            "-week_start",
            "-submitted_at",
        )
    )

    return render(
        request,
        "caregivers/assignment_detail.html",
        {
            "caregiver": caregiver,
            "assignment": assignment,
            "reports": reports,
            "weekly_reports": weekly_reports,

            "assignment_start": _assignment_start_date(
                assignment
            ),

            "assignment_end": _assignment_end_date(
                assignment
            ),

            "assignment_type_display": _assignment_type_display(
                assignment
            ),

            "status_display": assignment.get_status_display(),
        },
    )



# ============================================================
# ACCEPT ASSIGNMENT
# ============================================================

@login_required
@require_http_methods(["POST"])
def caregiver_assignment_accept(request, pk):
    """
    Caregiver accepts a pending assignment.
    """

    caregiver, assignment = _get_caregiver_assignment(
        request,
        pk,
    )

    if assignment.status != CaregiverAssignment.Status.PENDING:

        messages.warning(
            request,
            "This assignment is no longer awaiting your acceptance.",
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    response_note = (
        request.POST.get(
            "response_note",
            "",
        )
        .strip()
    )

    # --------------------------------------------------------
    # UPDATE ASSIGNMENT
    # --------------------------------------------------------

    assignment.status = CaregiverAssignment.Status.ACCEPTED
    assignment.accepted_at = timezone.now()
    assignment.declined_at = None
    assignment.caregiver_response_note = response_note

    assignment.save(
        update_fields=[
            "status",
            "accepted_at",
            "declined_at",
            "caregiver_response_note",
        ]
    )

    # --------------------------------------------------------
    # KEEP HOME CARE REQUEST SYNCHRONIZED
    # --------------------------------------------------------

    _set_homecare_assignment_status(
        assignment.homecare_request
    )

    # --------------------------------------------------------
    # STAFF NOTIFICATION
    # --------------------------------------------------------

    _notify_staff_assignment_response(
        assignment=assignment,
        action="ACCEPTED",
        note=response_note,
    )

    messages.success(
        request,
        "Assignment accepted successfully.",
    )

    return redirect(
        "caregivers:assignment_detail",
        pk=assignment.pk,
    )


# ============================================================
# DECLINE ASSIGNMENT
# ============================================================

@login_required
@require_http_methods(["POST"])
def caregiver_assignment_decline(request, pk):
    """
    Caregiver declines a pending assignment.

    A reason is required.
    """

    caregiver, assignment = _get_caregiver_assignment(
        request,
        pk,
    )

    if assignment.status != CaregiverAssignment.Status.PENDING:

        messages.warning(
            request,
            "This assignment is no longer awaiting your response.",
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    reason = (
        request.POST.get(
            "response_note",
            "",
        )
        .strip()
    )

    if not reason:

        messages.error(
            request,
            "Please provide a reason for declining the assignment.",
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    assignment.status = CaregiverAssignment.Status.DECLINED
    assignment.declined_at = timezone.now()
    assignment.accepted_at = None
    assignment.caregiver_response_note = reason

    assignment.save(
        update_fields=[
            "status",
            "declined_at",
            "accepted_at",
            "caregiver_response_note",
            
        ]
    )

    # --------------------------------------------------------
    # STAFF NOTIFICATION
    # --------------------------------------------------------

    _notify_staff_assignment_response(
        assignment=assignment,
        action="DECLINED",
        note=reason,
    )

    messages.warning(
        request,
        "The assignment has been declined. Staff have been notified.",
    )

    return redirect(
        "caregivers:assignments"
    )


# ============================================================
# START ASSIGNMENT
# ============================================================

@login_required
@require_http_methods(["POST"])
def caregiver_assignment_start(request, pk):
    """
    Start an accepted assignment.
    """

    caregiver, assignment = _get_caregiver_assignment(
        request,
        pk,
    )

    if assignment.status != CaregiverAssignment.Status.ACCEPTED:

        messages.warning(
            request,
            "Only an accepted assignment can be started.",
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    assignment.status = CaregiverAssignment.Status.IN_PROGRESS

    assignment.save(
        update_fields=[
            "status",
           
        ]
    )

    messages.success(
        request,
        "Assignment started. You can now submit daily reports.",
    )

    return redirect(
        "caregivers:assignment_detail",
        pk=assignment.pk,
    )


# ============================================================
# DAILY REPORT
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def caregiver_daily_report_create(request, pk):
    """
    Create or update a daily caregiver report.
    """

    caregiver, assignment = _get_caregiver_assignment(
        request,
        pk,
    )

    allowed_statuses = [
        CaregiverAssignment.Status.ACCEPTED,
        CaregiverAssignment.Status.IN_PROGRESS,
    ]

    blocked_statuses = [
        CaregiverAssignment.Status.COMPLETED,
        CaregiverAssignment.Status.CANCELLED,
        CaregiverAssignment.Status.DECLINED,
        CaregiverAssignment.Status.PENDING,
    ]

    if assignment.status in blocked_statuses:

        messages.error(
            request,
            "A report cannot be submitted for this assignment.",
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    if assignment.status not in allowed_statuses:

        messages.error(
            request,
            "Accept the assignment before submitting a daily report.",
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    start_date = _assignment_start_date(
        assignment
    )

    end_date = _assignment_end_date(
        assignment
    )

    if request.method == "POST":

        date_value = (
            request.POST.get(
                "report_date",
                "",
            )
            .strip()
        )

        try:

            report_date = datetime.strptime(
                date_value,
                "%Y-%m-%d",
            ).date()

        except (ValueError, TypeError):

            messages.error(
                request,
                "Please provide a valid report date.",
            )

            return redirect(
                "caregivers:daily_report_create",
                pk=assignment.pk,
            )

        if start_date and report_date < start_date:

            messages.error(
                request,
                "The report date cannot be before the assignment start date.",
            )

            return redirect(
                "caregivers:daily_report_create",
                pk=assignment.pk,
            )

        if end_date and report_date > end_date:

            messages.error(
                request,
                "The report date cannot be after the assignment end date.",
            )

            return redirect(
                "caregivers:daily_report_create",
                pk=assignment.pk,
            )

        defaults = {
            "patient_condition": (
                request.POST.get(
                    "patient_condition",
                    "STABLE",
                ).strip()
                or "STABLE"
            ),

            "vital_observations": (
                request.POST.get(
                    "vital_observations",
                    "",
                ).strip()
            ),

            "care_provided": (
                request.POST.get(
                    "care_provided",
                    "",
                ).strip()
            ),

            "patient_progress": (
                request.POST.get(
                    "patient_progress",
                    "",
                ).strip()
            ),

            "concerns": (
                request.POST.get(
                    "concerns",
                    "",
                ).strip()
            ),

            "caregiver_notes": (
                request.POST.get(
                    "caregiver_notes",
                    "",
                ).strip()
            ),
        }

        if not defaults["care_provided"]:

            messages.error(
                request,
                "Please describe the care provided.",
            )

            return redirect(
                "caregivers:daily_report_create",
                pk=assignment.pk,
            )

        if not defaults["patient_progress"]:

            messages.error(
                request,
                "Please describe the patient's progress.",
            )

            return redirect(
                "caregivers:daily_report_create",
                pk=assignment.pk,
            )

        # ----------------------------------------------------
        # VISIT START TIME
        # ----------------------------------------------------

        start_time_value = (
            request.POST.get(
                "visit_start_time",
                "",
            )
            .strip()
        )

        if start_time_value:

            try:

                defaults["visit_start_time"] = datetime.strptime(
                    start_time_value,
                    "%H:%M",
                ).time()

            except ValueError:

                messages.error(
                    request,
                    "Please provide a valid visit start time.",
                )

                return redirect(
                    "caregivers:daily_report_create",
                    pk=assignment.pk,
                )

        # ----------------------------------------------------
        # VISIT END TIME
        # ----------------------------------------------------

        end_time_value = (
            request.POST.get(
                "visit_end_time",
                "",
            )
            .strip()
        )

        if end_time_value:

            try:

                defaults["visit_end_time"] = datetime.strptime(
                    end_time_value,
                    "%H:%M",
                ).time()

            except ValueError:

                messages.error(
                    request,
                    "Please provide a valid visit end time.",
                )

                return redirect(
                    "caregivers:daily_report_create",
                    pk=assignment.pk,
                )

        # ----------------------------------------------------
        # NEXT VISIT
        # ----------------------------------------------------

        next_visit_date_value = (
            request.POST.get(
                "next_visit_date",
                "",
            )
            .strip()
        )

        if next_visit_date_value:

            try:

                defaults["next_visit_date"] = datetime.strptime(
                    next_visit_date_value,
                    "%Y-%m-%d",
                ).date()

            except ValueError:

                messages.error(
                    request,
                    "Please provide a valid next visit date.",
                )

                return redirect(
                    "caregivers:daily_report_create",
                    pk=assignment.pk,
                )

        else:

            defaults["next_visit_date"] = None

        report, created = (
            CaregiverDailyReport.objects.update_or_create(
                assignment=assignment,
                report_date=report_date,
                defaults=defaults,
            )
        )

        # ----------------------------------------------------
        # AUTOMATICALLY MOVE ACCEPTED → IN PROGRESS
        # ----------------------------------------------------

        if assignment.status == CaregiverAssignment.Status.ACCEPTED:

            assignment.status = (
                CaregiverAssignment.Status.IN_PROGRESS
            )

            assignment.save(
                update_fields=[
                    "status",
                   
                ]
            )

        messages.success(
            request,
            (
                "Daily report submitted successfully."
                if created
                else
                "Daily report updated successfully."
            ),
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    # --------------------------------------------------------
    # EXISTING REPORT FOR TODAY
    # --------------------------------------------------------

    existing_report = (
        CaregiverDailyReport.objects
        .filter(
            assignment=assignment,
            report_date=timezone.localdate(),
        )
        .first()
    )

    return render(
        request,
        "caregivers/daily_report_form.html",
        {
            "caregiver": caregiver,
            "assignment": assignment,
            "report": existing_report,
            "assignment_start": start_date,
            "assignment_end": end_date,
            "condition_choices": (
                CaregiverDailyReport
                .PatientCondition
                .choices
            ),
        },
    )


# ============================================================
# CAREGIVER REPORTS
# ============================================================

@login_required
@require_http_methods(["GET"])
def caregiver_reports(request):

    caregiver = _get_logged_in_caregiver(request)

    if caregiver is None:

        messages.error(
            request,
            "Your caregiver profile could not be found.",
        )

        return redirect(
            "caregivers:login"
        )

    reports = (
        CaregiverDailyReport.objects
        .select_related(
            "assignment",
            "assignment__homecare_request",
        )
        .filter(
            assignment__caregiver=caregiver
        )
        .order_by(
            "-report_date",
            "-submitted_at",
        )
    )

    return render(
        request,
        "caregivers/reports.html",
        {
            "caregiver": caregiver,
            "reports": reports,
        },
    )


# ============================================================
# WEEKLY SUMMARY
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def caregiver_weekly_summary(request, pk):
    """
    Display and submit a weekly summary.

    The summary is stored in CaregiverWeeklyReport.
    """

    caregiver, assignment = _get_caregiver_assignment(
        request,
        pk,
    )

    start_date = _assignment_start_date(
        assignment
    )

    end_date = _assignment_end_date(
        assignment
    )

    reports = (
        assignment.daily_reports
        .all()
        .order_by(
            "report_date",
            "submitted_at",
        )
    )

    if start_date and end_date:

        reports = reports.filter(
            report_date__gte=start_date,
            report_date__lte=end_date,
        )

    total_days = 0

    if start_date and end_date:

        total_days = (
            end_date - start_date
        ).days + 1

    submitted_days = (
        reports
        .values("report_date")
        .distinct()
        .count()
    )

    existing_summary = (
        CaregiverWeeklyReport.objects
        .filter(
            assignment=assignment,
            week_start=start_date,
            week_end=end_date,
        )
        .first()
        if start_date and end_date
        else None
    )

    return render(
        request,
        "caregivers/weekly_summary.html",
        {
            "caregiver": caregiver,
            "assignment": assignment,
            "assignment_start": start_date,
            "assignment_end": end_date,
            "assignment_type_display": (
                _assignment_type_display(
                    assignment
                )
            ),
            "reports": reports,
            "weekly_report": existing_summary,
            "total_days": total_days,
            "submitted_days": submitted_days,
            "outstanding_days": max(
                total_days - submitted_days,
                0,
            ),
        },
    )
# ============================================================
# STAFF ASSIGNMENT NOTIFICATION
# ============================================================

def _notify_staff_assignment_response(
    assignment,
    action,
    note="",
):
    """
    Notify staff when a caregiver accepts, declines or completes
    an assignment.

    This function deliberately does not fail the caregiver workflow
    if email configuration is unavailable.
    """

    from django.core.mail import mail_admins

    patient = assignment.homecare_request.full_name
    caregiver = assignment.caregiver.name

    subject = (
        f"Home Care Assignment {action}: "
        f"{patient}"
    )

    message = (
        f"Home Care Assignment Update\n\n"
        f"Patient: {patient}\n"
        f"Caregiver: {caregiver}\n"
        f"Action: {action}\n"
        f"Assignment ID: #{assignment.pk}\n\n"
    )

    if note:

        message += (
            f"Caregiver Response / Note:\n"
            f"{note}\n\n"
        )

    message += (
        "Please log into the Hands-On Health staff dashboard "
        "to review the assignment."
    )

    try:

        mail_admins(
            subject=subject,
            message=message,
            fail_silently=True,
        )

    except Exception:

        # Notification failure must not undo the assignment
        # status change.
        pass

# ============================================================
# COMPLETE ASSIGNMENT
# ============================================================

@login_required
@require_http_methods(["POST"])
def caregiver_assignment_complete(request, pk):

    caregiver, assignment = _get_caregiver_assignment(
        request,
        pk,
    )

    if assignment.status not in (
        CaregiverAssignment.Status.ACCEPTED,
        CaregiverAssignment.Status.IN_PROGRESS,
    ):

        messages.warning(
            request,
            "Only an accepted or in-progress assignment can be completed.",
        )

        return redirect(
            "caregivers:assignment_detail",
            pk=assignment.pk,
        )

    start_date = _assignment_start_date(
        assignment
    )

    end_date = _assignment_end_date(
        assignment
    )

    # --------------------------------------------------------
    # VERIFY ALL REQUIRED DAILY REPORTS
    # --------------------------------------------------------

    if start_date and end_date:

        expected_days = (
            end_date - start_date
        ).days + 1

        submitted_days = (
            assignment.daily_reports
            .filter(
                report_date__gte=start_date,
                report_date__lte=end_date,
            )
            .values("report_date")
            .distinct()
            .count()
        )

        if submitted_days < expected_days:

            messages.error(
                request,
                (
                    "Please submit all daily reports before "
                    "completing this assignment. "
                    f"{submitted_days} of "
                    f"{expected_days} day(s) have been reported."
                ),
            )

            return redirect(
                "caregivers:assignment_detail",
                pk=assignment.pk,
            )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    assignment.status = (
        CaregiverAssignment.Status.COMPLETED
    )

    assignment.completed_at = timezone.now()

    assignment.save(
        update_fields=[
            "status",
            "completed_at",
            
        ]
    )

    _set_homecare_completed(
        assignment.homecare_request
    )

    # --------------------------------------------------------
    # STAFF NOTIFICATION
    # --------------------------------------------------------

    _notify_staff_assignment_response(
        assignment=assignment,
        action="COMPLETED",
        note="Caregiver completed the assignment.",
    )

    messages.success(
        request,
        "Assignment marked as completed successfully.",
    )

    return redirect(
        "caregivers:assignments"
    )
# ============================================================
# CAREGIVER TOKEN DASHBOARD - LEGACY COMPATIBILITY
# ============================================================
#
# Existing email links use:
#     /caregiver/dashboard/<signed-token>/
#
# Keep that URL working, but make sure an authenticated caregiver
# can only open an assignment belonging to their own caregiver
# profile.
# ============================================================

@login_required
def caregiver_dashboard(request, token):
    try:
        assignment_id = signing.TimestampSigner().unsign(
            token,
            max_age=60 * 60 * 24 * 7,
        )
    except signing.BadSignature:
        messages.error(
            request,
            "This caregiver dashboard link is invalid or has expired.",
        )

        return render(
            request,
            "homecare/caregiver_link_expired.html",
            {
                "message": (
                    "This caregiver dashboard link is invalid "
                    "or has expired."
                ),
            },
        )

    caregiver = _get_logged_in_caregiver(request)

    assignment = get_object_or_404(
        _caregiver_assignment_queryset(),
        id=assignment_id,
        caregiver=caregiver,
    )

    return redirect(
        "caregivers:assignment_detail",
        pk=assignment.pk,
    )




# ============================================================
# ADMIN DASHBOARD
# ============================================================

@login_required
def admin_dashboard(request):

    if not (
        request.user.is_superuser
        or getattr(request.user, "role", None) == "ADMIN"
    ):
        raise Http404

    total_caregivers = Caregiver.objects.count()
    active_caregivers = Caregiver.objects.filter(is_active=True).count()
    pending_caregivers = Caregiver.objects.filter(
        verification_status="PENDING_VERIFICATION"
    ).count()

    total_homecare_requests = HomeCareRequest.objects.count()
    pending_payments = Payment.objects.filter(
        status=Payment.Status.PENDING
    ).count()
    pending_consultations = Consultation.objects.filter(
        status=Consultation.Status.PENDING
    ).count()

    recent_caregivers = Caregiver.objects.all().order_by("-id")[:5]
    recent_requests = HomeCareRequest.objects.all().order_by("-id")[:5]

    recent_payments = (
        Payment.objects.select_related(
            "quotation",
            "quotation__homecare_request",
            "quotation__consultation",
        )
        .order_by("-id")[:5]
    )

    return render(
        request,
        "homecare/admin_dashboard.html",
        {
            "total_caregivers": total_caregivers,
            "active_caregivers": active_caregivers,
            "pending_caregivers": pending_caregivers,
            "total_homecare_requests": total_homecare_requests,
            "pending_payments": pending_payments,
            "pending_consultations": pending_consultations,
            "recent_caregivers": recent_caregivers,
            "recent_requests": recent_requests,
            "recent_payments": recent_payments,
        },
    )