from django.urls import reverse

from testimonials.models import Testimonial
from testimonials.forms import TestimonialForm
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


def reviews(request):
    """Display approved testimonials and process new public submissions.

    New testimonials require staff approval before publication.
    """
    if request.method == "POST":
        form = TestimonialForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            testimonial = form.save(commit=False)

            # Public submissions must never self-approve.
            testimonial.status = Testimonial.Status.PENDING
            testimonial.approved_at = None

            if request.user.is_authenticated:
                testimonial.submitted_by = request.user

            testimonial.save()

            messages.success(
                request,
                "Thank you for sharing your experience! "
                "Your testimonial has been submitted for review.",
            )

            # Set session flag to hide form on successful submit
            request.session["form_submitted"] = True

            return redirect(reverse("pages:reviews"))

        messages.error(request, "Please correct the errors in the testimonial form.")

    else:
        form = TestimonialForm()

    # Read and reset session flag
    form_submitted = request.session.pop("form_submitted", False)

    approved_testimonials = Testimonial.objects.filter(
        status=Testimonial.Status.APPROVED,
        consent_to_publish=True,
    ).order_by("-approved_at", "-created_at")

    context = {
        "form": form,
        "testimonials": approved_testimonials,
        "faqs": public_faqs(),
        "form_submitted": form_submitted,
    }

    return render(
        request,
        "pages/reviews.html",
        context,
    )
