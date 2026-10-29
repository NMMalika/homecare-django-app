from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_GET


@require_GET
def robots_txt(request):
    if settings.DEBUG:
        lines = ["User-agent: *", "Disallow: /"]
    else:
        lines = [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /staff/",
            "Disallow: /caregiver/",
            "Disallow: /chatbot/",
            "Disallow: /home-care/quotation/",
            "Disallow: /home-care/payment/",
            "Disallow: /home-care/appointment/",
            "Sitemap: "
            + request.build_absolute_uri(
                reverse("django.contrib.sitemaps.views.sitemap")
            ),
        ]
    return HttpResponse(
        "\n".join(lines) + "\n", content_type="text/plain; charset=utf-8"
    )
