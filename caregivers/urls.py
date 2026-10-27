from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from . import views
from .forms import CaregiverPasswordResetForm

from homecare import views as homecare_views


app_name = "caregivers"


urlpatterns = [
    # =========================================================
    # AUTHENTICATION
    # =========================================================
    path(
        "login/",
        views.caregiver_login,
        name="login",
    ),
    path(
        "register/<str:token>/",
        views.caregiver_register_invitation,
        name="register_invitation",
    ),
    path(
        "logout/",
        views.caregiver_logout,
        name="logout",
    ),
    # =========================================================
    # CAREGIVER PASSWORD RESET
    # =========================================================
    # STEP 1: Enter email address
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="caregivers/password_reset.html",
            email_template_name="caregivers/emails/password_reset_email.txt",
            subject_template_name="caregivers/emails/password_reset_subject.txt",
            form_class=CaregiverPasswordResetForm,
            success_url=reverse_lazy("caregivers:password_reset_done"),
        ),
        name="password_reset",
    ),
    # STEP 2: Email sent confirmation
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="caregivers/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    # STEP 3: Open secure link and enter new password
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="caregivers/password_reset_confirm.html",
            success_url=reverse_lazy("caregivers:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    # STEP 4: Password successfully changed
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="caregivers/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    # =========================================================
    # DASHBOARD
    # =========================================================
    path(
        "dashboard/",
        views.caregiver_dashboard,
        name="dashboard",
    ),
    # =========================================================
    # PROFILE
    # =========================================================
    path(
        "profile/",
        views.caregiver_profile,
        name="profile",
    ),
    # =========================================================
    # ASSIGNMENTS
    # Business logic is handled by homecare.views
    # =========================================================
    path(
        "assignments/",
        homecare_views.caregiver_assignments,
        name="assignments",
    ),
    path(
        "assignments/<int:pk>/",
        homecare_views.caregiver_assignment_detail,
        name="assignment_detail",
    ),
    path(
        "assignments/<int:pk>/accept/",
        homecare_views.caregiver_assignment_accept,
        name="assignment_accept",
    ),
    path(
        "assignments/<int:pk>/decline/",
        homecare_views.caregiver_assignment_decline,
        name="assignment_decline",
    ),
    path(
        "assignments/<int:pk>/start/",
        homecare_views.caregiver_assignment_start,
        name="assignment_start",
    ),
    path(
        "assignments/<int:pk>/report/",
        homecare_views.caregiver_daily_report_create,
        name="daily_report_create",
    ),
    path(
        "assignments/<int:pk>/complete/",
        homecare_views.caregiver_assignment_complete,
        name="assignment_complete",
    ),
    # =========================================================
    # REPORTS
    # =========================================================
    path(
        "reports/",
        homecare_views.caregiver_reports,
        name="reports",
    ),
    path(
        "assignments/<int:pk>/weekly-summary/",
        homecare_views.caregiver_weekly_summary,
        name="weekly_summary",
    ),
    path("careers/", views.caregiver_public_apply, name="careers"),
    path(
        "application-success/",
        views.caregiver_application_success,
        name="application_success",
    ),
]
