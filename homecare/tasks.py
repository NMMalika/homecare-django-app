
# ============================================================
# tasks.py
#
# Requires Celery + Redis (or another Celery broker).
#
# Add this app's tasks to your Celery setup.
# ============================================================

from datetime import datetime, timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from .models import Consultation


@shared_task
def send_consultation_reminders():

    now = timezone.now()

    consultations = Consultation.objects.select_related(
        "homecare_request",
        "doctor",
    ).filter(
        status=Consultation.Status.SCHEDULED,
        consultation_date__isnull=False,
        consultation_time__isnull=False,
    )

    for consultation in consultations:

        appointment = timezone.make_aware(
            datetime.combine(
                consultation.consultation_date,
                consultation.consultation_time,
            ),
            timezone.get_current_timezone(),
        )

        seconds_until = (appointment - now).total_seconds()

        patient = consultation.homecare_request
        doctor_email = consultation.doctor.email

        # 3-hour reminder window.
        if (
            not consultation.reminder_3h_sent
            and 2.9 * 3600 <= seconds_until <= 3.1 * 3600
        ):
            _send_reminder(
                consultation,
                patient.email,
                doctor_email,
                "3 hours",
            )

            consultation.reminder_3h_sent = True
            consultation.save(
                update_fields=[
                    "reminder_3h_sent",
                    "updated_at",
                ]
            )

        # 1-hour reminder window.
        if (
            not consultation.reminder_1h_sent
            and 0.9 * 3600 <= seconds_until <= 1.1 * 3600
        ):
            _send_reminder(
                consultation,
                patient.email,
                doctor_email,
                "1 hour",
            )

            consultation.reminder_1h_sent = True
            consultation.save(
                update_fields=[
                    "reminder_1h_sent",
                    "updated_at",
                ]
            )


def _send_reminder(
    consultation,
    patient_email,
    doctor_email,
    remaining,
):

    patient = consultation.homecare_request

    subject = (
        f"Telemedicine Consultation Reminder - "
        f"{remaining} remaining"
    )

    patient_message = (
        f"Dear {patient.full_name},\n\n"
        f"This is a reminder that your home-care "
        f"telemedicine consultation is in {remaining}.\n\n"
        f"Date: {consultation.consultation_date}\n"
        f"Time: {consultation.consultation_time}\n\n"
        f"Join here:\n"
        f"{consultation.patient_join_url}\n\n"
        f"Please keep your consultation link private."
    )

    if patient_email:
        send_mail(
            subject,
            patient_message,
            None,
            [patient_email],
            fail_silently=True,
        )

    if doctor_email:
        doctor_message = (
            f"Reminder: you have a home-care telemedicine "
            f"consultation in {remaining}.\n\n"
            f"Patient: {patient.full_name}\n"
            f"Date: {consultation.consultation_date}\n"
            f"Time: {consultation.consultation_time}\n\n"
            f"Doctor link:\n"
            f"{consultation.doctor_join_url}"
        )

        send_mail(
            subject,
            doctor_message,
            None,
            [doctor_email],
            fail_silently=True,
        )