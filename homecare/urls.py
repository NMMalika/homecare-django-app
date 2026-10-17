
from django.urls import path

from . import views


app_name = "homecare"


urlpatterns = [

    # =========================================================
    # HOME CARE
    # =========================================================

    path(
        "",
        views.request_home_care,
        name="request",
    ),

    path(
        "success/",
        views.request_success,
        name="success",
    ),


    # =========================================================
    # REFERRAL
    # =========================================================

    path(
        "referral/",
        views.refer_a_patient,
        name="referral",
    ),

    path(
        "referral/success/",
        views.referral_success,
        name="referral_success",
    ),


    # =========================================================
    # BOOK APPOINTMENT / CONSULTATION
    # =========================================================
    #
    # Completely separate from HomeCareRequest.
    # =========================================================

    path(
        "appointment/",
        views.book_appointment,
        name="book_appointment",
    ),

    path(
        "appointment/success/",
        views.appointment_success,
        name="appointment_success",
    ),


    # =========================================================
    # HOME CARE QUOTATION
    # =========================================================

    path(
        "quotation/<int:request_id>/",
        views.create_quotation,
        name="create_quotation",
    ),


    # =========================================================
    # CONSULTATION QUOTATION
    # =========================================================

    path(
        "consultation/<int:consultation_id>/quotation/",
        views.create_consultation_quotation,
        name="create_consultation_quotation",
    ),


    # =========================================================
    # VIEW QUOTATION
    # Works for both Home Care and Consultation
    # =========================================================

    path(
        "quotation/view/<str:token>/",
        views.quotation_detail,
        name="quotation_detail",
    ),


    # =========================================================
    # PAYMENT
    # =========================================================

    path(
        "quotation/payment/<str:token>/submit/",
        views.submit_payment,
        name="submit_payment",
    ),

    path(
        "quotation/payment-submitted/<str:token>/",
        views.payment_submitted,
        name="payment_submitted",
    ),

    path(
        "payment/<int:payment_id>/verify/",
        views.verify_payment,
        name="verify_payment",
    ),


    # =========================================================
    # CONSULTATION MANUAL SLOT MANAGEMENT
    # =========================================================
    #
    # Admin:
    # 1. Opens consultation
    # 2. Creates available slots
    # 3. Can remove slots
    # 4. Sends availability to patient
    #
    # Calendly is no longer used.
    # =========================================================

    path(
        "consultations/<int:consultation_id>/schedule/",
        views.schedule_consultation,
        name="schedule_consultation",
    ),

    path(
        "consultations/slots/<int:slot_id>/delete/",
        views.delete_consultation_slot,
        name="delete_consultation_slot",
    ),

    path(
        "consultations/<int:consultation_id>/send-availability/",
        views.send_consultation_availability,
        name="send_consultation_availability",
    ),


    # =========================================================
    # PATIENT CONSULTATION SLOT SELECTION
    # =========================================================
    #
    # Patient receives secure link by email.
    # Patient opens available slots.
    # Patient selects ONE slot.
    # =========================================================

    path(
        "consultation/availability/<str:token>/",
        views.consultation_availability,
        name="consultation_availability",
    ),

    path(
        "consultation/availability/<str:token>/select/<int:slot_id>/",
        views.select_consultation_slot,
        name="select_consultation_slot",
    ),

    path(
        "consultation/scheduled/<str:token>/",
        views.consultation_scheduled,
        name="consultation_scheduled",
    ),


    # =========================================================
    # TELEMEDICINE
    # =========================================================

    path(
        "telemedicine/patient/<str:token>/",
        views.patient_telemedicine,
        name="patient_telemedicine",
    ),

    path(
        "telemedicine/patient/<str:token>/status/",
        views.patient_telemedicine_status,
        name="patient_telemedicine_status",
    ),

    path(
        "telemedicine/doctor/<str:token>/",
        views.doctor_telemedicine,
        name="doctor_telemedicine",
    ),


    # =========================================================
    # CONSULTATION START / COMPLETE
    # =========================================================

    path(
        "consultations/<int:consultation_id>/start/",
        views.start_consultation,
        name="start_consultation",
    ),

    path(
        "consultations/<int:consultation_id>/complete/",
        views.complete_consultation,
        name="complete_consultation",
    ),


    # =========================================================
    # CAREGIVER ASSIGNMENTS
    # =========================================================
    #
    # SINGLE SOURCE OF TRUTH
    #
    # All caregiver assignment business logic lives in
    # homecare.views.
    #
    # The caregivers app calls these views from its own
    # caregiver-facing URLs.
    # =========================================================

    path(
        "caregiver/assignments/",
        views.caregiver_assignments,
        name="caregiver_assignments",
    ),

    path(
        "caregiver/assignments/<int:pk>/",
        views.caregiver_assignment_detail,
        name="caregiver_assignment_detail",
    ),

    path(
        "caregiver/assignments/<int:pk>/accept/",
        views.caregiver_assignment_accept,
        name="caregiver_assignment_accept",
    ),

    path(
        "caregiver/assignments/<int:pk>/decline/",
        views.caregiver_assignment_decline,
        name="caregiver_assignment_decline",
    ),

    path(
        "caregiver/assignments/<int:pk>/start/",
        views.caregiver_assignment_start,
        name="caregiver_assignment_start",
    ),

    path(
        "caregiver/assignments/<int:pk>/report/",
        views.caregiver_daily_report_create,
        name="caregiver_daily_report_create",
    ),

    path(
        "caregiver/assignments/<int:pk>/complete/",
        views.caregiver_assignment_complete,
        name="caregiver_assignment_complete",
    ),


    # =========================================================
    # CAREGIVER REPORTS
    # =========================================================

    path(
        "caregiver/reports/",
        views.caregiver_reports,
        name="caregiver_reports",
    ),

    path(
        "caregiver/assignments/<int:pk>/weekly-summary/",
        views.caregiver_weekly_summary,
        name="caregiver_weekly_summary",
    ),
]

