from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from homecare.models import (
    Caregiver,
    CaregiverCertificate,
    CaregiverAssignment,
)
from .forms import CaregiverLoginForm


# ============================================================
# CAREGIVER LOGIN
# ============================================================

@require_http_methods(["GET", "POST"])
def caregiver_login(request):
    """
    Caregiver login.

    Only users with the CAREGIVER role and an approved/active
    caregiver profile are allowed into the caregiver portal.
    """

    if request.user.is_authenticated:
        if getattr(request.user, "role", None) == User.Role.CAREGIVER:
            return redirect("caregivers:dashboard")

        logout(request)

    form = CaregiverLoginForm(request, data=request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()

            if getattr(user, "role", None) != User.Role.CAREGIVER:
                messages.error(
                    request,
                    "This login is for caregivers only.",
                )
                return redirect("caregivers:login")

            try:
                caregiver = user.caregiver_profile
            except Caregiver.DoesNotExist:
                messages.error(
                    request,
                    "Your caregiver profile could not be found. "
                    "Please contact the administrator.",
                )
                return redirect("caregivers:login")

            if not caregiver.is_active:
                messages.error(
                    request,
                    "Your caregiver account is not currently active. "
                    "Please contact the administrator.",
                )
                return redirect("caregivers:login")

            if caregiver.verification_status != Caregiver.VerificationStatus.APPROVED:
                messages.error(
                    request,
                    "Your caregiver profile has not yet been approved.",
                )
                return redirect("caregivers:login")

            login(request, user)

            next_url = request.POST.get("next") or request.GET.get("next")

            if next_url and next_url.startswith("/"):
                return redirect(next_url)

            messages.success(
                request,
                f"Welcome back, {caregiver.name}.",
            )

            return redirect("caregivers:dashboard")

    return render(
        request,
        "caregivers/login.html",
        {
            "form": form,
        },
    )


# ============================================================
# CAREGIVER REGISTRATION
# ============================================================

@require_http_methods(["GET", "POST"])
def caregiver_register(request):
    """
    Register a new caregiver.

    New caregiver accounts remain inactive until verified
    by an administrator.
    """

    if request.user.is_authenticated:
        if getattr(request.user, "role", None) == User.Role.CAREGIVER:
            return redirect("caregivers:dashboard")

        logout(request)

    if request.method == "POST":
        with transaction.atomic():

            first_name = request.POST.get(
                "first_name",
                "",
            ).strip()

            last_name = request.POST.get(
                "last_name",
                "",
            ).strip()

            email = request.POST.get(
                "email",
                "",
            ).strip().lower()

            phone = request.POST.get(
                "phone",
                "",
            ).strip()

            professional_title = request.POST.get(
                "professional_title",
                "",
            ).strip()

            specialization = request.POST.get(
                "specialization",
                "",
            ).strip()

            password = request.POST.get(
                "password",
                "",
            )

            password_confirm = request.POST.get(
                "password_confirm",
                "",
            )

            cv = request.FILES.get("cv")

            cover_letter = request.FILES.get("cover_letter")

            licence_file = request.FILES.get("licence_file")

            licence_number = request.POST.get(
                "licence_number",
                "",
            ).strip()

            licence_name = request.POST.get(
                "licence_name",
                "",
            ).strip()

            certificates = request.FILES.getlist(
                "certificates"
            )

            # ------------------------------------------------
            # BASIC VALIDATION
            # ------------------------------------------------

            if not first_name:
                messages.error(
                    request,
                    "Please enter your first name.",
                )
                return render(
                    request,
                    "caregivers/register.html",
                )

            if not last_name:
                messages.error(
                    request,
                    "Please enter your last name.",
                )
                return render(
                    request,
                    "caregivers/register.html",
                )

            if not email:
                messages.error(
                    request,
                    "Please enter your email address.",
                )
                return render(
                    request,
                    "caregivers/register.html",
                )

            if not password:
                messages.error(
                    request,
                    "Please enter a password.",
                )
                return render(
                    request,
                    "caregivers/register.html",
                )

            if password != password_confirm:
                messages.error(
                    request,
                    "Passwords do not match.",
                )
                return render(
                    request,
                    "caregivers/register.html",
                )

            if User.objects.filter(
                email__iexact=email
            ).exists():
                messages.error(
                    request,
                    "An account with this email already exists.",
                )
                return render(
                    request,
                    "caregivers/register.html",
                )

            # ------------------------------------------------
            # CREATE USER
            # ------------------------------------------------

            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.CAREGIVER,
                is_active=False,
            )

            # ------------------------------------------------
            # CREATE CAREGIVER PROFILE
            # ------------------------------------------------

            caregiver = Caregiver.objects.create(
                user=user,
                name=f"{first_name} {last_name}".strip(),
                professional_title=professional_title,
                specialization=specialization,
                phone=phone,
                email=email,
                is_active=False,
                verification_status=Caregiver.VerificationStatus.PENDING,
                cv=cv,
            )

            # ------------------------------------------------
            # SAVE CERTIFICATES
            # ------------------------------------------------

            for certificate in certificates:
                CaregiverCertificate.objects.create(
                    caregiver=caregiver,
                    certificate=certificate,
                )

            # ------------------------------------------------
            # OPTIONAL FILES
            #
            # Only save these if the fields actually exist
            # on your Caregiver model.
            # ------------------------------------------------

            caregiver_fields = {
                field.name
                for field in Caregiver._meta.get_fields()
            }

            if "cover_letter" in caregiver_fields:
                caregiver.cover_letter = cover_letter

            if "licence_file" in caregiver_fields:
                caregiver.licence_file = licence_file

            if "licence_number" in caregiver_fields:
                caregiver.licence_number = licence_number

            if "licence_name" in caregiver_fields:
                caregiver.licence_name = licence_name

            fields_to_update = []

            for field_name in (
                "cover_letter",
                "licence_file",
                "licence_number",
                "licence_name",
            ):
                if field_name in caregiver_fields:
                    fields_to_update.append(field_name)

            if fields_to_update:
                caregiver.save(
                    update_fields=fields_to_update
                )

            # ------------------------------------------------
            # STORE PENDING REGISTRATION IN SESSION
            # ------------------------------------------------

            request.session["caregiver_pending_user_id"] = user.pk
            request.session["caregiver_pending_profile_id"] = caregiver.pk

        messages.success(
            request,
            "Your caregiver registration has been submitted successfully. "
            "Your account will be activated after administrator verification.",
        )

        return redirect("caregivers:login")

    return render(
        request,
        "caregivers/register.html",
    )



@login_required
def caregiver_dashboard(request):
    """
    Caregiver dashboard.

    Shows the caregiver's real assignment statistics and
    provides access to the caregiver assignment portal.
    """

    # ---------------------------------------------------------
    # VERIFY USER ROLE
    # ---------------------------------------------------------

    if request.user.role != User.Role.CAREGIVER:
        messages.error(
            request,
            "Only caregiver accounts can access this dashboard."
        )
        return redirect("caregivers:login")


    # ---------------------------------------------------------
    # GET CAREGIVER PROFILE
    # ---------------------------------------------------------

    try:
        caregiver = request.user.caregiver_profile

    except Caregiver.DoesNotExist:
        messages.error(
            request,
            "Your caregiver profile could not be found."
        )
        return redirect("caregivers:login")


    # ---------------------------------------------------------
    # VERIFY CAREGIVER ACCOUNT
    # ---------------------------------------------------------

    if not caregiver.is_active:

        messages.warning(
            request,
            "Your caregiver account is not active."
        )

        return redirect("caregivers:login")


    # ---------------------------------------------------------
    # GET ALL ASSIGNMENTS FOR THIS CAREGIVER
    # ---------------------------------------------------------

    assignments = (
        CaregiverAssignment.objects
        .filter(caregiver=caregiver)
        .select_related("homecare_request")
        .order_by("-assigned_at", "-id")
    )


    # ---------------------------------------------------------
    # CALCULATE REAL COUNTS
    # ---------------------------------------------------------

    # Convert queryset to list once so we can safely work with it
    # and still pass it to the template.

    assignment_list = list(assignments)


    pending_count = 0
    active_count = 0
    completed_count = 0


    # Get the actual status values from your model.

    for assignment in assignment_list:

        status = str(assignment.status).upper()


        # -----------------------------------------------------
        # PENDING
        # -----------------------------------------------------

        if status in [
            "PENDING",
            "PENDING_ACCEPTANCE",
        ]:

            pending_count += 1


        # -----------------------------------------------------
        # ACTIVE
        # -----------------------------------------------------

        elif status in [
            "ACCEPTED",
            "IN_PROGRESS",
            "ASSIGNED",
        ]:

            active_count += 1


        # -----------------------------------------------------
        # COMPLETED
        # -----------------------------------------------------

        elif status in [
            "COMPLETED",
        ]:

            completed_count += 1


    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {

        "caregiver": caregiver,

        "assignments": assignment_list,

        "pending_count": pending_count,

        "active_count": active_count,

        "completed_count": completed_count,

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

    if getattr(request.user, "role", None) != User.Role.CAREGIVER:
        messages.error(
            request,
            "Only caregivers can access this page.",
        )
        return redirect("caregivers:login")

    try:
        caregiver = request.user.caregiver_profile
    except Caregiver.DoesNotExist:
        messages.error(
            request,
            "Your caregiver profile could not be found.",
        )
        return redirect("caregivers:login")

    if request.method == "POST":

        caregiver.name = request.POST.get(
            "name",
            caregiver.name,
        ).strip()

        caregiver.professional_title = request.POST.get(
            "professional_title",
            caregiver.professional_title,
        ).strip()

        caregiver.specialization = request.POST.get(
            "specialization",
            caregiver.specialization,
        ).strip()

        caregiver.phone = request.POST.get(
            "phone",
            caregiver.phone,
        ).strip()

        caregiver.email = request.POST.get(
            "email",
            caregiver.email,
        ).strip()

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
        {
            "caregiver": caregiver,
        },
    )


# ============================================================
# CAREGIVER LOGOUT
# ============================================================

@require_http_methods(["GET", "POST"])
def caregiver_logout(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully.",
    )

    return redirect("caregivers:login")