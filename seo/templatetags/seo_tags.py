# seo/templatetags/seo_tags.py

import json

from django import template
from django.utils.html import format_html
from django.utils.html import strip_tags
from django.utils.text import Truncator

from core.models import SiteSettings
from services.models import Service
from staff.models import FAQItem

register = template.Library()


def render_jsonld(data):
    """
    Safely render structured data inside a script tag.
    """
    serialized = json.dumps(
        data,
        ensure_ascii=False,
    ).replace("<", "\\u003c")

    return format_html(
        '<script type="application/ld+json">{}</script>',
        serialized,
    )


def absolute_url(request, path):
    return request.build_absolute_uri(path)


@register.simple_tag
def canonical_url(request):
    """
    Return the current page URL without query parameters.
    """
    if request is None:
        return ""

    return request.build_absolute_uri(request.path)


@register.simple_tag
def business_jsonld(request):
    """
    Generate structured data using the business settings.
    Updates automatically when staff edit SiteSettings.
    """

    if request is None:
        return ""

    settings = SiteSettings.objects.first()

    if settings is None:
        return ""

    website = (
        settings.website.rstrip("/")
        if settings.website
        else request.build_absolute_uri("/").rstrip("/")
    )

    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": website + "/#organization",
        "name": settings.business_name,
        "url": website,
    }

    if settings.tagline:
        data["description"] = settings.tagline

    if settings.logo:
        data["logo"] = absolute_url(
            request,
            settings.logo.url,
        )

    if settings.phone:
        data["telephone"] = settings.phone

    if settings.email:
        data["email"] = settings.email

    address = {
        "@type": "PostalAddress",
    }

    if settings.address:
        address["streetAddress"] = settings.address

    if settings.city:
        address["addressLocality"] = settings.city

    if settings.country:
        address["addressCountry"] = settings.country

    if len(address) > 1:
        data["address"] = address

    social_links = [
        settings.facebook,
        settings.instagram,
        settings.linkedin,
        settings.tiktok,
        settings.youtube,
    ]

    social_links = [link for link in social_links if link]

    if social_links:
        data["sameAs"] = social_links

    return render_jsonld(data)


@register.simple_tag
def faq_jsonld():
    """
    Generate FAQ schema from active FAQ records.
    Use only on a page displaying these FAQs.
    """

    faqs = FAQItem.objects.filter(is_active=True).order_by("display_order", "id")

    questions = []

    for faq in faqs:
        if not faq.question or not faq.answer:
            continue

        questions.append(
            {
                "@type": "Question",
                "name": faq.question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": strip_tags(faq.answer),
                },
            }
        )

    if not questions:
        return ""

    return render_jsonld(
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": questions,
        }
    )


@register.simple_tag
def services_jsonld(request):
    """
    Generate service information from active services.
    Use on a page listing these active services.
    """

    if request is None:
        return ""

    services = (
        Service.objects.filter(is_active=True)
        .select_related("category")
        .order_by("order", "name")
    )

    items = []

    for position, service in enumerate(services, start=1):

        description = service.short_description or service.description or service.name

        service_data = {
            "@type": "Service",
            "name": service.name,
            "description": Truncator(strip_tags(description)).chars(500),
        }

        if service.category:
            service_data["serviceType"] = service.category.name

        if service.image:
            service_data["image"] = absolute_url(
                request,
                service.image.url,
            )

        items.append(
            {
                "@type": "ListItem",
                "position": position,
                "item": service_data,
            }
        )

    if not items:
        return ""

    return render_jsonld(
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": items,
        }
    )
