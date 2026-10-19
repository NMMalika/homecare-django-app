
from django.shortcuts import render
from django.db.models import Prefetch

from services.models import Service, ServiceCategory
from staff.models import FAQItem


def public_faqs():
    """
    Return active FAQs in display order.
    """
    return FAQItem.objects.filter(
        is_active=True
    ).order_by("display_order", "id")

def faq(request):
    """
    Display the main Frequently Asked Questions page.
    """
    return render(request, "pages/faq.html")


def home(request):
    """
    Public homepage.
    Supplies active FAQs to home.html so the FAQ section
    can display questions managed through the staff dashboard.
    """
    active_services = (
        Service.objects
        .filter(is_active=True)
        .order_by("order", "name")
    )

    categories = (
        ServiceCategory.objects
        .filter(services__is_active=True)
        .distinct()
        .prefetch_related(
            Prefetch(
                "services",
                queryset=active_services,
            )
        )
        .order_by("order", "name")
    )

    context = {
        "categories": categories,
        "faqs": public_faqs(),
    }

    return render(request, "home.html", context)


def about(request):
    return render(
        request,
        "pages/about.html",
        {"faqs": public_faqs()},
    )


def how_it_works(request):
    return render(
        request,
        "pages/how_it_works.html",
        {"faqs": public_faqs()},
    )


def professionals(request):
    return render(
        request,
        "pages/professionals.html",
        {"faqs": public_faqs()},
    )


def contact(request):
    return render(
        request,
        "pages/contact.html",
        {"faqs": public_faqs()},
    )


def services(request):
    active_services = (
        Service.objects
        .filter(is_active=True)
        .order_by("order", "name")
    )

    categories = (
        ServiceCategory.objects
        .filter(services__is_active=True)
        .distinct()
        .prefetch_related(
            Prefetch(
                "services",
                queryset=active_services,
            )
        )
        .order_by("order", "name")
    )

    context = {
        "categories": categories,
        "faqs": public_faqs(),
    }

    return render(request, "pages/services.html", context)
