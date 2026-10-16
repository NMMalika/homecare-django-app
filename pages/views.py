from django.shortcuts import render
from django.db.models import Prefetch

from services.models import Service, ServiceCategory

def about(request):

    return render(
        request,
        "pages/about.html"
    )


def how_it_works(request):

    return render(
        request,
        "pages/how_it_works.html"
    )


def professionals(request):

    return render(
        request,
        "pages/professionals.html"
    )


def contact(request):

    return render(
        request,
        "pages/contact.html"
    )
# ============================================================
# PUBLIC SERVICES PAGE
# ============================================================
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

    return render(
        request,
        "pages/services.html",
        {
            "categories": categories,
        },
    )