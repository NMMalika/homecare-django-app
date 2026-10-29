from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PublicPagesSitemap(Sitemap):
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        return [
            "home",
            "pages:about",
            "pages:services",
            "pages:how_it_works",
            "pages:professionals",
            "pages:contact",
            "pages:faq",
            "pages:reviews",
        ]

    def location(self, item):
        return reverse(item)
