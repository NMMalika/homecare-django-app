from django.shortcuts import render

from services.models import ServiceCategory


def home(request):
    categories = ServiceCategory.objects.prefetch_related("services").all()

    # Appointment form errors/data returned from the
    # homecare.book_appointment view
    appointment_errors = request.session.pop(
        "appointment_errors",
        []
    )

    appointment_form_data = request.session.pop(
        "appointment_form_data",
        {}
    )

    return render(
        request,
        "home.html",
        {
            "categories": categories,
            "appointment_errors": appointment_errors,
            "appointment_form_data": appointment_form_data,
        },
    )


def about(request):
    return render(request, "pages/about.html")


def services(request):
    categories = ServiceCategory.objects.prefetch_related(
        "services"
    ).all()

    return render(
        request,
        "pages/services.html",
        {
            "categories": categories,
        },
    )


def home_care(request):
    return render(request, "home-care.html")


def referral(request):
    return render(request, "referral.html")


def contact(request):
    return render(request, "pages/contact.html")


def appointment(request):
    return render(request, "pages/appointment.html")