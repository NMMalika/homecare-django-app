from functools import wraps

from django.contrib import admin, messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

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
    HomeCareRequest,
    Consultation,
    Payment,
    Quotation,
    Referral,
)

from homecare.views import (
    verify_payment as homecare_verify_payment,
    send_caregiver_assignment_email,
)


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

            next_url = (
                request.POST.get("next")
                or request.GET.get("next")
            )

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect(
                "staff:dashboard"
            )

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

    return redirect(
        "staff:login"
    )


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

            return redirect(
                "staff:dashboard"
            )

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

    recent_requests = (
        HomeCareRequest.objects
        .order_by("-created_at")[:5]
    )

    recent_appointments = (
        Consultation.objects
        .select_related("doctor")
        .order_by("-created_at")[:5]
    )

    recent_payments = (
        Payment.objects
        .select_related(
            "quotation",
            "quotation__homecare_request",
            "quotation__consultation",
            "verified_by",
        )
        .order_by("-submitted_at")[:5]
    )

    recent_quotations = (
        Quotation.objects
        .select_related(
            "homecare_request",
            "consultation",
        )
        .order_by("-created_at")[:5]
    )

    recent_assignments = (
        CaregiverAssignment.objects
        .select_related(
            "caregiver",
            "homecare_request",
            "assigned_by",
        )
        .order_by("-assigned_at")[:5]
    )

    context = {

        "site_settings": SiteSettings.load(),

        "pending_caregivers": pending_caregivers,

        "caregiver_count": (
            Caregiver.objects.count()
        ),

        "assignment_count": (
            CaregiverAssignment.objects.count()
        ),

        "homecare_request_count": (
            HomeCareRequest.objects.count()
        ),

        "appointment_count": (
            Consultation.objects.count()
        ),

        "payment_count": (
            Payment.objects.count()
        ),

        "quotation_count": (
            Quotation.objects.count()
        ),

        "report_count": (
            CaregiverDailyReport.objects.count()
        ),

        "caregiver_payment_count": (
            CaregiverPayment.objects.count()
        ),

        "recent_requests": recent_requests,

        "recent_appointments": recent_appointments,

        "recent_payments": recent_payments,

        "recent_quotations": recent_quotations,

        "recent_assignments": recent_assignments,
    }

    return render(
        request,
        "staff/dashboard.html",
        context,
    )


# ============================================================
# CAREGIVERS
# ============================================================

@admin_required
def caregivers(request):

    current_status = request.GET.get(
        "status",
        "",
    )

    search = request.GET.get(
        "q",
        "",
    ).strip()

    caregivers_queryset = (
        Caregiver.objects
        .select_related("user")
        .prefetch_related("certificates")
        .order_by("name")
    )

    if current_status:

        caregivers_queryset = caregivers_queryset.filter(
            verification_status=current_status
        )

    if search:

        caregivers_queryset = caregivers_queryset.filter(
            Q(name__icontains=search)
            |
            Q(user__first_name__icontains=search)
            |
            Q(user__last_name__icontains=search)
            |
            Q(user__email__icontains=search)
        )

    verification_choices = (
        Caregiver.VerificationStatus.choices
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

            "verification_choices": verification_choices,

            "pending_caregivers": pending_caregivers,

            "search": search,

            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# CAREGIVER VERIFICATION
# ============================================================

@admin_required
def caregiver_verify(request, pk):

    caregiver = get_object_or_404(
        Caregiver.objects
        .select_related(
            "user",
            "approved_by",
        )
        .prefetch_related("certificates"),
        pk=pk,
    )

    if request.method == "POST":

        action = request.POST.get(
            "action"
        )

        comment = request.POST.get(
            "comment",
            "",
        ).strip()

        # ----------------------------------------------------
        # APPROVE
        # ----------------------------------------------------

        if action == "approve":

            caregiver.verification_status = (
                Caregiver.VerificationStatus.APPROVED
            )

            caregiver.is_active = True

            caregiver.verification_notes = comment

            caregiver.approved_by = request.user

            caregiver.approved_at = timezone.now()

            caregiver.save()

            if caregiver.user:

                caregiver.user.is_active = True

                caregiver.user.save(
                    update_fields=[
                        "is_active",
                    ]
                )

            messages.success(
                request,
                f"{caregiver.name} has been approved.",
            )

            return redirect(
                "staff:caregivers"
            )

        # ----------------------------------------------------
        # DECLINE
        # ----------------------------------------------------

        elif action == "decline":

            caregiver.verification_status = (
                Caregiver.VerificationStatus.REJECTED
            )

            caregiver.is_active = False

            caregiver.verification_notes = comment

            caregiver.save()

            if caregiver.user:

                caregiver.user.is_active = False

                caregiver.user.save(
                    update_fields=[
                        "is_active",
                    ]
                )

            messages.warning(
                request,
                f"{caregiver.name} has been declined.",
            )

            return redirect(
                "staff:caregivers"
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
        CaregiverAssignment.objects
        .select_related(
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
            Q(
                caregiver__name__icontains=search
            )
            |
            Q(
                caregiver__user__first_name__icontains=search
            )
            |
            Q(
                caregiver__user__last_name__icontains=search
            )
            |
            Q(
                caregiver__user__email__icontains=search
            )
        )

    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    if current_status:

        assignments_queryset = assignments_queryset.filter(
            status=current_status
        )

    return render(
        request,
        "staff/assignments.html",
        {
            "assignments": assignments_queryset,

            "current_status": current_status,

            "search": search,

            "status_choices": (
                CaregiverAssignment.Status.choices
            ),

            "site_settings": SiteSettings.load(),
        },
    )




# ============================================================
# ADD CAREGIVER ASSIGNMENT
# ============================================================

@admin_required
def caregiver_assignment_add(request):

    request_id = (
        request.POST.get("homecare_request")
        or request.GET.get("homecare_request")
    )

    selected_request = None

    if request_id:
        selected_request = get_object_or_404(
            HomeCareRequest.objects.prefetch_related(
                "services"
            ),
            pk=request_id,
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form = CaregiverAssignmentForm(
            request.POST
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

                posted_request_id = request.POST.get(
                    "homecare_request"
                )

                if posted_request_id:

                    selected_request = get_object_or_404(
                        HomeCareRequest.objects.prefetch_related(
                            "services"
                        ),
                        pk=posted_request_id,
                    )

        else:

            try:

                # ====================================================
                # CREATE ASSIGNMENT
                # ====================================================

                with transaction.atomic():

                    assignment = form.save(
                        commit=False
                    )

                    # ------------------------------------------------
                    # KEEP SELECTED HOME CARE REQUEST
                    # ------------------------------------------------

                    if selected_request:

                        assignment.homecare_request = (
                            selected_request
                        )

                    # ------------------------------------------------
                    # RECORD STAFF MEMBER
                    # ------------------------------------------------

                    assignment.assigned_by = request.user

                    # ------------------------------------------------
                    # NEW ASSIGNMENTS WAIT FOR ACCEPTANCE
                    # ------------------------------------------------

                    assignment.status = (
                        CaregiverAssignment.Status.PENDING
                    )

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

                    homecare_request = (
                        assignment.homecare_request
                    )

                    if homecare_request:

                        homecare_request.status = (
                            HomeCareRequest.Status.ASSIGNED
                        )

                        homecare_request.save(
                            update_fields=[
                                "status",
                                "updated_at",
                            ]
                        )

                # ====================================================
                # SEND CAREGIVER EMAIL
                # ====================================================
                #
                # IMPORTANT:
                # The database transaction has completed successfully
                # before we attempt the email.
                #
                # Pass the assignment first and the Django request
                # second.
                # ====================================================

                try:

                    # Make sure we have the caregiver.
                    caregiver = assignment.caregiver

                    if caregiver is None:

                        raise ValueError(
                            "No caregiver was selected for this assignment."
                        )

                    # Make sure caregiver has an email.
                    caregiver_email = (
                        getattr(
                            caregiver,
                            "email",
                            None,
                        )
                        or getattr(
                            getattr(
                                caregiver,
                                "user",
                                None,
                            ),
                            "email",
                            None,
                        )
                    )

                    if not caregiver_email:

                        raise ValueError(
                            "The assigned caregiver does not have "
                            "an email address."
                        )

                    # ------------------------------------------------
                    # SEND
                    # ------------------------------------------------

                    send_caregiver_assignment_email(
                        
                        request,
                        assignment,
                    )

                    messages.success(
                        request,
                        (
                            "Caregiver assignment created successfully "
                            f"and the notification email was sent to "
                            f"{caregiver_email}."
                        ),
                    )

                except Exception as email_error:

                    # ------------------------------------------------
                    # EMAIL FAILED
                    # ------------------------------------------------
                    #
                    # The assignment remains saved.
                    # Show the REAL error instead of hiding it.
                    # ------------------------------------------------

                    messages.error(
                        request,
                        (
                            "The caregiver assignment was created, "
                            "BUT the caregiver email could not be sent. "
                            f"Email error: {email_error}"
                        ),
                    )

                return redirect(
                    "staff:assignments"
                )

            except Exception as e:

                messages.error(
                    request,
                    (
                        "The caregiver assignment could not be "
                        f"created. Error: {e}"
                    ),
                )

    # ========================================================
    # GET
    # ========================================================

    else:

        initial = {}

        if selected_request:

            initial["homecare_request"] = (
                selected_request.pk
            )

            if getattr(
                selected_request,
                "preferred_date",
                None,
            ):

                initial["service_date"] = (
                    selected_request.preferred_date
                )

            if getattr(
                selected_request,
                "preferred_time",
                None,
            ):

                initial["service_time"] = (
                    selected_request.preferred_time
                )

        form = CaregiverAssignmentForm(
            initial=initial
        )

    # ========================================================
    # REQUESTED SERVICES
    # ========================================================

    services = (
        selected_request.services.all()
        if selected_request
        else []
    )

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
        CaregiverAssignment.objects
        .select_related(
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
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    # ------------------------------------------------
                    # SAVE FORM WITHOUT FINAL STATUS
                    # ------------------------------------------------

                    assignment = form.save(
                        commit=False
                    )

                    # ------------------------------------------------
                    # RECORD STAFF MEMBER
                    # ------------------------------------------------

                    assignment.assigned_by = request.user

                    # ------------------------------------------------
                    # EVERY STAFF REASSIGNMENT RETURNS TO
                    # PENDING ACCEPTANCE
                    # ------------------------------------------------

                    assignment.status = (
                        CaregiverAssignment.Status.PENDING
                    )

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

                    homecare_request = (
                        assignment.homecare_request
                    )

                    homecare_request.status = (
                        HomeCareRequest.Status.ASSIGNED
                    )

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
                    if (
                        original_caregiver.pk
                        != assignment.caregiver.pk
                    ):

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

                return redirect(
                    "staff:assignments"
                )

            except Exception as e:

                messages.error(
                    request,
                    (
                        "The caregiver assignment could not be "
                        f"updated. Error: {e}"
                    ),
                )

    else:

        form = CaregiverAssignmentForm(
            instance=assignment,
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

        return redirect(
            "staff:assignments"
        )

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

    requests_queryset = (
        HomeCareRequest.objects
        .prefetch_related("services")
        .order_by("-created_at")
    )

    if search:

        requests_queryset = requests_queryset.filter(
            Q(full_name__icontains=search)
            |
            Q(phone__icontains=search)
            |
            Q(email__icontains=search)
            |
            Q(address__icontains=search)
            |
            Q(city__icontains=search)
        )

    if current_status:

        requests_queryset = requests_queryset.filter(
            status=current_status
        )

    return render(
        request,
        "staff/homecare_requests.html",
        {
            "homecare_requests": requests_queryset,

            "current_status": current_status,

            "search": search,

            "status_choices": (
                HomeCareRequest.Status.choices
            ),

            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# ADD HOME CARE REQUEST
# ============================================================

@admin_required
def homecare_request_add(request):

    if request.method == "POST":

        form = HomeCareRequestForm(
            request.POST
        )

        if form.is_valid():

            homecare_request = form.save(
                commit=False
            )

            if not homecare_request.status:

                homecare_request.status = (
                    HomeCareRequest.Status.NEW
                )

            homecare_request.save()

            form.save_m2m()

            messages.success(
                request,
                (
                    f'Home care request for '
                    f'"{homecare_request.full_name}" '
                    f'has been created successfully.'
                ),
            )

            return redirect(
                "staff:homecare_requests"
            )

    else:

        form = HomeCareRequestForm(
            initial={
                "status": HomeCareRequest.Status.NEW
            }
        )

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
                    f'Home care request for '
                    f'"{homecare_request.full_name}" '
                    f'has been updated successfully.'
                ),
            )

            return redirect(
                "staff:homecare_requests"
            )

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

            "title": (
                f"Edit Home Care Request - "
                f"{homecare_request.full_name}"
            ),

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
                f'Home care request for '
                f'"{patient_name}" '
                f'has been deleted successfully.'
            ),
        )

        return redirect(
            "staff:homecare_requests"
        )

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
        Referral.objects
        .select_related(
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

    appointments_queryset = (
        Consultation.objects
        .select_related("doctor")
        .order_by(
            "-created_at"
        )
    )

    if current_status:

        appointments_queryset = appointments_queryset.filter(
            status=current_status
        )

    if appointment_id:

        if appointment_id.isdigit():

            appointments_queryset = appointments_queryset.filter(
                pk=appointment_id
            )

    return render(
        request,
        "staff/appointments.html",
        {
            "appointments": appointments_queryset,

            "current_status": current_status,

            "selected_appointment_id": appointment_id,

            "status_choices": (
                Consultation.Status.choices
            ),

            "site_settings": SiteSettings.load(),
        },
    )


# ============================================================
# QUOTATIONS
# ============================================================

@admin_required
def quotations(request):

    quotations_queryset = (
        Quotation.objects
        .select_related(
            "homecare_request",
            "consultation",
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "staff/quotations.html",
        {
            "quotations": quotations_queryset,

            "site_settings": SiteSettings.load(),
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

        client_name = str(
            consultation
        )

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

    reports_queryset = (
        CaregiverDailyReport.objects
        .select_related(
            "assignment",
            "assignment__caregiver",
            "assignment__homecare_request",
            "reviewed_by",
        )
        .order_by(
            "-report_date",
            "-submitted_at",
        )
    )

    if search:

        reports_queryset = reports_queryset.filter(
            Q(
                assignment__caregiver__name__icontains=search
            )
            |
            Q(
                assignment__caregiver__user__first_name__icontains=search
            )
            |
            Q(
                assignment__caregiver__user__last_name__icontains=search
            )
        )

    if condition:

        reports_queryset = reports_queryset.filter(
            patient_condition=condition
        )

    condition_field = (
        CaregiverDailyReport._meta.get_field(
            "patient_condition"
        )
    )

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

        form = CaregiverDailyReportForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Caregiver daily report created successfully.",
            )

            return redirect(
                "staff:reports"
            )

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

            return redirect(
                "staff:reports"
            )

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

        return redirect(
            "staff:reports"
        )

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

    payments_queryset = (
        CaregiverPayment.objects
        .select_related(
            "caregiver",
            "assignment",
            "assignment__homecare_request",
        )
        .order_by(
            "-created_at"
        )
    )

    if search:

        payments_queryset = payments_queryset.filter(
            Q(
                caregiver__name__icontains=search
            )
            |
            Q(
                caregiver__user__first_name__icontains=search
            )
            |
            Q(
                caregiver__user__last_name__icontains=search
            )
            |
            Q(
                caregiver__user__email__icontains=search
            )
        )

    if current_status:

        payments_queryset = payments_queryset.filter(
            status=current_status
        )

    status_field = (
        CaregiverPayment._meta.get_field(
            "status"
        )
    )

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

        form = CaregiverPaymentForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Caregiver payment created successfully.",
            )

            return redirect(
                "staff:caregiver_payments"
            )

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

            return redirect(
                "staff:caregiver_payments"
            )

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

        return redirect(
            "staff:caregiver_payments"
        )

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
        Service.objects
        .select_related("category")
        .all()
        .order_by(
            "order",
            "name",
        )
    )

    if search:

        services_queryset = services_queryset.filter(
            Q(name__icontains=search)
            |
            Q(category__name__icontains=search)
            |
            Q(short_description__icontains=search)
            |
            Q(description__icontains=search)
        )

    if category:

        services_queryset = services_queryset.filter(
            category_id=category
        )

    if active == "yes":

        services_queryset = services_queryset.filter(
            is_active=True
        )

    elif active == "no":

        services_queryset = services_queryset.filter(
            is_active=False
        )

    categories = (
        ServiceCategory.objects
        .all()
        .order_by(
            "order",
            "name",
        )
    )

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        selected_ids = request.POST.getlist(
            "selected_services"
        )

        if not selected_ids:

            messages.warning(
                request,
                "Please select at least one service.",
            )

            return redirect(
                "staff:services"
            )

        selected_services = Service.objects.filter(
            id__in=selected_ids
        )

        if action == "activate":

            updated = selected_services.update(
                is_active=True
            )

            messages.success(
                request,
                f"{updated} service(s) activated successfully.",
            )

        elif action == "deactivate":

            updated = selected_services.update(
                is_active=False
            )

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

        return redirect(
            "staff:services"
        )

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

    categories = (
        ServiceCategory.objects
        .all()
        .order_by(
            "order",
            "name",
        )
    )

    if request.method == "POST":

        post_data = request.POST.copy()

        new_category_name = post_data.get(
            "new_category",
            "",
        ).strip()

        created_category = None

        if new_category_name:

            new_category_name = new_category_name[:150]

            existing_category = (
                ServiceCategory.objects
                .filter(
                    name__iexact=new_category_name
                )
                .first()
            )

            if existing_category:

                category = existing_category

            else:

                category = ServiceCategory.objects.create(
                    name=new_category_name
                )

                created_category = category

            post_data["category"] = str(
                category.pk
            )

        form = ServiceForm(
            post_data,
            request.FILES,
        )

        if form.is_valid():

            service = form.save()

            messages.success(
                request,
                f'"{service.name}" has been added successfully.',
            )

            return redirect(
                "staff:services"
            )

        if created_category:

            if not Service.objects.filter(
                category=created_category
            ).exists():

                created_category.delete()

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

    service = get_object_or_404(
        Service,
        pk=pk,
    )

    categories = (
        ServiceCategory.objects
        .all()
        .order_by(
            "order",
            "name",
        )
    )

    if request.method == "POST":

        post_data = request.POST.copy()

        new_category_name = post_data.get(
            "new_category",
            "",
        ).strip()

        created_category = None

        if new_category_name:

            new_category_name = new_category_name[:150]

            existing_category = (
                ServiceCategory.objects
                .filter(
                    name__iexact=new_category_name
                )
                .first()
            )

            if existing_category:

                category = existing_category

            else:

                category = ServiceCategory.objects.create(
                    name=new_category_name
                )

                created_category = category

            post_data["category"] = str(
                category.pk
            )

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

            return redirect(
                "staff:services"
            )

        if created_category:

            if not Service.objects.filter(
                category=created_category
            ).exists():

                created_category.delete()

    else:

        form = ServiceForm(
            instance=service,
        )

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

        return redirect(
            "staff:services"
        )

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

            return redirect(
                "staff:settings"
            )

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