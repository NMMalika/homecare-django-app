from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
import json

from services.models import Service
from staff.models import FAQItem


def json_ld(data):
    return mark_safe(
        json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False).replace(
            "<", "\\u003c"
        )
    )


def service_schema(request):
    services = Service.objects.filter(is_active=True)

    items = []

    for service in services:
        items.append(
            {
                "@type": "Service",
                "name": service.name,
                "description": service.description,
                "areaServed": {"@type": "City", "name": "Windhoek"},
            }
        )

    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": index, "item": item}
            for index, item in enumerate(items, start=1)
        ],
    }


def faq_schema():
    faqs = FAQItem.objects.filter(is_active=True)

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq.question,
                "acceptedAnswer": {"@type": "Answer", "text": faq.answer},
            }
            for faq in faqs
        ],
    }
