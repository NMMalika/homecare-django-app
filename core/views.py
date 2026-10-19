
from django.shortcuts import render
from django.db.models import Prefetch

from services.models import ServiceCategory
from staff.models import FAQItem


def public_faqs():
    """
    Return active FAQs for public-facing pages.
    """
    return FAQItem.objects.filter(
        is_active=True
    ).order_by("display_order", "id")


def home(request):
    categories = ServiceCategory.objects.prefetch_related(
        "services"
    ).all()

    # Appointment form errors/data returned from the
    # homecare.book_appointment view.
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
            "faqs": public_faqs(),
        },
    )


def about(request):
    return render(
        request,
        "pages/about.html",
        {"faqs": public_faqs()},
    )


def services(request):
    categories = ServiceCategory.objects.prefetch_related(
        "services"
    ).all()

    return render(
        request,
        "pages/services.html",
        {
            "categories": categories,
            "faqs": public_faqs(),
        },
    )


def home_care(request):
    return render(
        request,
        "home-care.html",
        {"faqs": public_faqs()},
    )


def referral(request):
    return render(
        request,
        "referral.html",
        {"faqs": public_faqs()},
    )


def contact(request):
    return render(
        request,
        "pages/contact.html",
        {"faqs": public_faqs()},
    )


def appointment(request):
    return render(
        request,
        "pages/appointment.html",
        {"faqs": public_faqs()},
    )


def faq(request):
    """
    Display the dedicated Frequently Asked Questions page.
    The reusable FAQ include remains unchanged.
    """
    return render(
        request,
        "pages/faq.html",
        {"faqs": public_faqs()},
    )
