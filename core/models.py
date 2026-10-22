
from django.db import models


class SiteSettings(models.Model):

    business_name = models.CharField(
        max_length=200,
        default="Hands-On Health",
    )

    tagline = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)

    notification_emails = models.TextField(
        blank=True,
        help_text=(
            "Enter staff notification email addresses, "
            "separated by commas or new lines. "
            "Example: admin@example.com, reception@example.com"
        ),
    )

    phone = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    emergency_phone = models.CharField(max_length=50, blank=True)

    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Namibia")

    website = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)
    youtube = models.URLField(blank=True)

    logo = models.ImageField(
        upload_to="site/",
        blank=True,
        null=True,
    )

    favicon = models.ImageField(
        upload_to="site/",
        blank=True,
        null=True,
    )

    google_maps_url = models.URLField(blank=True)
    google_business_url = models.URLField(blank=True)

    # =========================================================
    # BANK TRANSFER
    # =========================================================

    bank_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=100, blank=True)
    branch_name = models.CharField(max_length=200, blank=True)

    # =========================================================
    # PAYFAST - MANUAL PAYMENT
    # =========================================================

    payfast_enabled = models.BooleanField(
        default=False,
        help_text="Allow patients to select PayFast for manual payments.",
    )

    payfast_payment_url = models.URLField(
        max_length=500,
        blank=True,
        help_text=(
            "Your PayFast hosted payment or payment-request link, "
            "if available."
        ),
    )

    payfast_instructions = models.TextField(
        blank=True,
        help_text=(
            "Instructions for patients paying externally "
            "through PayFast."
        ),
    )

    # =========================================================
    # PAYPAL - MANUAL PAYMENT
    # =========================================================

    paypal_enabled = models.BooleanField(
        default=False,
        help_text="Allow patients to select PayPal for manual payments.",
    )

    paypal_email = models.EmailField(
        blank=True,
        help_text="Your PayPal Business Account email address.",
    )

    paypal_payment_url = models.URLField(
        max_length=500,
        blank=True,
        help_text=(
            "Your PayPal payment link or payment-request URL, "
            "if available."
        ),
    )

    paypal_instructions = models.TextField(
        blank=True,
        help_text=(
            "Instructions for patients paying externally "
            "through PayPal."
        ),
    )

    # =========================================================
    # GENERAL PAYMENT INSTRUCTIONS
    # =========================================================

    payment_instructions = models.TextField(
        blank=True,
        help_text=(
            "Additional payment instructions shown to "
            "clients on quotations and payment pages."
        ),
    )

    # =========================================================
    # TIMESTAMPS
    # =========================================================

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "business_name": "Hands-On Health",
            },
        )
        return settings
