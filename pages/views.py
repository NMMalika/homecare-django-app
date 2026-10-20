
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Prefetch

from services.models import Service, ServiceCategory
from staff.models import FAQItem
from staff.models import ContactEnquiry


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
    """Display the contact page and process submitted enquiries."""

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
            Prefetch("services", queryset=active_services)
        )
        .order_by("order", "name")
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        service_value = request.POST.get("service", "").strip()
        town = request.POST.get("town", "").strip()
        message_text = request.POST.get("message", "").strip()

        errors = []

        if not name:
            errors.append("Please enter your full name.")

        if not email:
            errors.append("Please enter your email address.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Please enter a valid email address.")

        if not phone:
            errors.append("Please enter your phone number.")

        if not service_value:
            errors.append("Please select a service.")

        if not message_text:
            errors.append("Please enter your message.")

        selected_service = None
        is_general_enquiry = service_value == "other"

        if service_value and not is_general_enquiry:
            if service_value.isdigit():
                selected_service = active_services.filter(
                    pk=int(service_value)
                ).first()

            if selected_service is None:
                errors.append(
                    "The selected service is invalid or unavailable."
                )

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            ContactEnquiry.objects.create(
                name=name,
                email=email,
                phone=phone,
                service=selected_service,
                is_general_enquiry=is_general_enquiry,
                town=town,
                message=message_text,
            )

            messages.success(
                request,
                "Thank you for contacting Hands-On Health. "
                "Your enquiry has been submitted successfully."
            )
            return redirect("/pages/contact/")

    context = {
        "categories": categories,
        "services": active_services,
        "faqs": public_faqs(),
    }

    return render(request, "pages/contact.html", context)

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
