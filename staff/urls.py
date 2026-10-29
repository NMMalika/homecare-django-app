from django.urls import path

from . import views

app_name = "staff"

urlpatterns = [
    # =========================================================
    # AUTHENTICATION
    # =========================================================
    path(
        "login/",
        views.staff_login,
        name="login",
    ),
    path(
        "logout/",
        views.staff_logout,
        name="logout",
    ),
    path(
        "change-password/",
        views.change_password,
        name="change_password",
    ),
    # =========================================================
    # DASHBOARD
    # =========================================================
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),
    # =========================================================
    # CAREGIVERS
    # =========================================================
    path(
        "caregivers/",
        views.caregivers,
        name="caregivers",
    ),
    path(
        "caregivers/add/",
        views.caregiver_add,
        name="caregiver_add",
    ),
    # Review and approve or decline a caregiver
    path(
        "caregivers/<int:pk>/verify/",
        views.caregiver_verify,
        name="caregiver_verify",
    ),
    # Resend caregiver registration invitation
    path(
        "caregivers/<int:pk>/send-invitation/",
        views.caregiver_send_invitation,
        name="caregiver_send_invitation",
    ),
    # =========================================================
    # CAREGIVER ASSIGNMENTS
    # =========================================================
    # Main assignment list
    path(
        "assignments/",
        views.caregiver_assignments,
        name="assignments",
    ),
    # Compatibility alias for existing templates
    path(
        "assignments/",
        views.caregiver_assignments,
        name="caregiver_assignments",
    ),
    # Add an assignment
    path(
        "assignments/add/",
        views.caregiver_assignment_add,
        name="caregiver_assignment_add",
    ),
    # Compatibility alias
    path(
        "assignments/add/",
        views.caregiver_assignment_add,
        name="assignment_add",
    ),
    # Edit an assignment
    path(
        "assignments/<int:pk>/edit/",
        views.caregiver_assignment_edit,
        name="caregiver_assignment_edit",
    ),
    # Compatibility alias
    path(
        "assignments/<int:pk>/edit/",
        views.caregiver_assignment_edit,
        name="assignment_edit",
    ),
    # Delete an assignment
    path(
        "assignments/<int:pk>/delete/",
        views.caregiver_assignment_delete,
        name="caregiver_assignment_delete",
    ),
    # Compatibility alias
    path(
        "assignments/<int:pk>/delete/",
        views.caregiver_assignment_delete,
        name="assignment_delete",
    ),
    # =========================================================
    # CAREGIVER DAILY REPORTS
    # =========================================================
    path(
        "reports/",
        views.caregiver_daily_reports,
        name="reports",
    ),
    path(
        "reports/add/",
        views.caregiver_daily_report_add,
        name="report_add",
    ),
    path(
        "reports/<int:pk>/edit/",
        views.caregiver_daily_report_edit,
        name="report_edit",
    ),
    path(
        "reports/<int:pk>/delete/",
        views.caregiver_daily_report_delete,
        name="report_delete",
    ),
    # =========================================================
    # HOME CARE REQUESTS
    # =========================================================
    path(
        "homecare/",
        views.homecare_requests,
        name="homecare_requests",
    ),
    path(
        "homecare/add/",
        views.homecare_request_add,
        name="homecare_request_add",
    ),
    path(
        "homecare/<int:pk>/edit/",
        views.homecare_request_edit,
        name="homecare_request_edit",
    ),
    path(
        "homecare/<int:pk>/delete/",
        views.homecare_request_delete,
        name="homecare_request_delete",
    ),
    # =========================================================
    # REFERRALS
    # =========================================================
    path(
        "referrals/",
        views.referrals,
        name="referrals",
    ),
    # =========================================================
    # CONSULTATIONS / APPOINTMENTS
    # =========================================================
    path(
        "appointments/",
        views.appointments,
        name="appointments",
    ),
    path(
        "consultations/<int:consultation_id>/quotation/",
        views.consultation_quotation,
        name="consultation_quotation",
    ),
    # =========================================================
    # QUOTATIONS
    # =========================================================
    path(
        "quotations/",
        views.quotations,
        name="quotations",
    ),
    path(
        "quotations/<int:pk>/",
        views.quotation_detail,
        name="quotation_detail",
    ),
    # =========================================================
    # PAYMENTS
    # =========================================================
    path(
        "payments/",
        views.payments,
        name="payments",
    ),
    path(
        "payments/<int:payment_id>/verify/",
        views.payment_verify,
        name="payment_verify",
    ),
    # =========================================================
    # CAREGIVER PAYMENTS
    # =========================================================
    path(
        "caregiver-payments/",
        views.caregiver_payments,
        name="caregiver_payments",
    ),
    path(
        "caregiver-payments/add/",
        views.caregiver_payment_add,
        name="caregiver_payment_add",
    ),
    path(
        "caregiver-payments/<int:pk>/edit/",
        views.caregiver_payment_edit,
        name="caregiver_payment_edit",
    ),
    path(
        "caregiver-payments/<int:pk>/delete/",
        views.caregiver_payment_delete,
        name="caregiver_payment_delete",
    ),
    # =========================================================
    # SERVICES
    # =========================================================
    path(
        "services/",
        views.services,
        name="services",
    ),
    path(
        "services/add/",
        views.service_add,
        name="service_add",
    ),
    path(
        "services/<int:pk>/edit/",
        views.service_edit,
        name="service_edit",
    ),
    path(
        "services/<int:pk>/delete/",
        views.service_delete,
        name="service_delete",
    ),
    # =========================================================
    # SETTINGS
    # =========================================================
    path(
        "settings/",
        views.settings,
        name="settings",
    ),
    # =========================================================
    # FAQ / CUSTOMER QUESTIONS
    # =========================================================
    path(
        "questions/dashboard/",
        views.questions_dashboard_view,
        name="questions_dashboard",
    ),
    path(
        "ask-question/",
        views.ask_question,
        name="ask_question",
    ),
    path(
        "questions/",
        views.question_inbox,
        name="question_inbox",
    ),
    path(
        "questions/<int:question_id>/",
        views.question_reply,
        name="question_reply",
    ),
    path("faqs/", views.faq_list, name="faq_list"),
    path("faqs/add/", views.faq_create, name="faq_create"),
    path("faqs/<int:pk>/edit/", views.faq_edit, name="faq_edit"),
    path("faqs/<int:pk>/delete/", views.faq_delete, name="faq_delete"),
    path(
        "contact-enquiries/",
        views.contact_enquiries,
        name="contact_enquiries",
    ),
    path(
        "contact-enquiries/<int:pk>/reply/",
        views.contact_enquiry_reply,
        name="contact_enquiry_reply",
    ),
    path(
        "testimonials/",
        views.testimonials,
        name="testimonials",
    ),
    path(
        "testimonials/<int:pk>/moderate/",
        views.testimonial_moderate,
        name="testimonial_moderate",
    ),
    path(
        "about-us/",
        views.about_us_edit,
        name="about_us_edit",
    ),
    path(
        "hero-slides/",
        views.hero_slides,
        name="hero_slides",
    ),
    path(
        "hero-slides/<int:position>/",
        views.hero_slide_edit,
        name="hero_slide_edit",
    ),
]

from . import chatbot_views

urlpatterns += [
    path(
        "chatbot/knowledge/",
        chatbot_views.chatbot_knowledge_list,
        name="chatbot_knowledge_list",
    ),
    path(
        "chatbot/knowledge/add/",
        chatbot_views.chatbot_knowledge_create,
        name="chatbot_knowledge_create",
    ),
    path(
        "chatbot/knowledge/<int:pk>/edit/",
        chatbot_views.chatbot_knowledge_edit,
        name="chatbot_knowledge_edit",
    ),
    path(
        "chatbot/knowledge/<int:pk>/toggle/",
        chatbot_views.chatbot_knowledge_toggle,
        name="chatbot_knowledge_toggle",
    ),
    path(
        "chatbot/knowledge/<int:pk>/delete/",
        chatbot_views.chatbot_knowledge_delete,
        name="chatbot_knowledge_delete",
    ),
]
from . import chatbot_unanswered_views

urlpatterns += [
    path(
        "chatbot/unanswered/",
        chatbot_unanswered_views.unanswered_questions,
        name="chatbot_unanswered",
    ),
    path(
        "chatbot/unanswered/<int:pk>/train/",
        chatbot_unanswered_views.chatbot_unanswered_train,
        name="chatbot_unanswered_train",
    ),
    path(
        "chatbot/unanswered/<int:pk>/ignore/",
        chatbot_unanswered_views.chatbot_unanswered_ignore,
        name="chatbot_unanswered_ignore",
    ),
    path(
        "chatbot/unanswered/<int:pk>/status/",
        chatbot_unanswered_views.update_unanswered_status,
        name="chatbot_unanswered_status",
    ),
]
from . import chatbot_training_views

urlpatterns += [
    path(
        "chatbot/training/",
        chatbot_training_views.chatbot_training,
        name="chatbot_training",
    ),
    path(
        "chatbot/training/<int:pk>/incorrect/",
        chatbot_training_views.chatbot_mark_incorrect,
        name="chatbot_mark_incorrect",
    ),
    path(
        "chatbot/training/<int:pk>/answer/",
        chatbot_training_views.chatbot_train_answer,
        name="chatbot_train_answer",
    ),
]
