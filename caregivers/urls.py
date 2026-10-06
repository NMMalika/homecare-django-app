from django.urls import path

from . import views
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
        "register/",
        views.caregiver_register,
        name="register",
    ),

    path(
        "logout/",
        views.caregiver_logout,
        name="logout",
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
]