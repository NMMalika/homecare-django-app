
from django.shortcuts import render
from django.db.models import Prefetch

from services.models import ServiceCategory
from staff.models import FAQItem
from hero.models import HeroSlide


def public_faqs():
    """
    Return active FAQs for public-facing pages.
    """
    return FAQItem.objects.filter(
        is_active=True
    ).order_by("display_order", "id")


def home(request):
    """
    Display the homepage with services, hero slides, FAQs,
    and any appointment form errors or previously entered data.
    """
    categories = ServiceCategory.objects.prefetch_related(
        "services"
    ).all()

    # Load active hero slides from the database in display order.
    hero_slides = HeroSlide.objects.filter(
        is_active=True
    ).order_by("position")

    # Retrieve appointment form errors and data from the session.
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
            "hero_slides": hero_slides,
            "appointment_errors": appointment_errors,
            "appointment_form_data": appointment_form_data,
            "faqs": public_faqs(),
        },
    )


def about(request):
    return render(
        request,
        "pages/about.html",
        {
            "faqs": public_faqs(),
        },
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
        {
            "faqs": public_faqs(),
        },
    )


def referral(request):
    return render(
        request,
        "referral.html",
        {
            "faqs": public_faqs(),
        },
    )


def contact(request):
    return render(
        request,
        "pages/contact.html",
        {
            "faqs": public_faqs(),
        },
    )


def appointment(request):
    return render(
        request,
        "pages/appointment.html",
        {
            "faqs": public_faqs(),
        },
    )


def faq(request):
    """
    Display the dedicated Frequently Asked Questions page.
    The reusable FAQ include remains unchanged.
    """
    return render(
        request,
        "pages/faq.html",
        {
            "faqs": public_faqs(),
        },
    )
