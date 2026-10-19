
from staff.models import FAQItem


def public_faqs(request):
    """
    Make active FAQs available to all Django templates.
    """
    return {
        "faqs": FAQItem.objects.filter(
            is_active=True
        ).order_by("display_order", "id")
    }
