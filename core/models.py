from django.db import models


class SiteSettings(models.Model):

    business_name = models.CharField(
        max_length=200,
        default="Hands-On Health",
    )

    tagline = models.CharField(
        max_length=255,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )
    
    notification_emails = models.TextField(
    blank=True,
    help_text=(
        "Enter staff notification email addresses, "
        "separated by commas or new lines. "
        "Example: admin@example.com, "
        "reception@example.com"
    ),
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    whatsapp = models.CharField(
        max_length=50,
        blank=True,
    )

    emergency_phone = models.CharField(
        max_length=50,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        default="Namibia",
    )

    website = models.URLField(
        blank=True,
    )

    facebook = models.URLField(
        blank=True,
    )

    instagram = models.URLField(
        blank=True,
    )

    linkedin = models.URLField(
        blank=True,
    )

    tiktok = models.URLField(
        blank=True,
    )

    youtube = models.URLField(
        blank=True,
    )

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

    google_maps_url = models.URLField(
        blank=True,
    )

    google_business_url = models.URLField(
        blank=True,
    )

        # =========================================================
    # PAYMENT INFORMATION
    # =========================================================

    # =========================================================
    # BANK TRANSFER
    # =========================================================

    bank_name = models.CharField(
        max_length=200,
        blank=True,
    )

    account_name = models.CharField(
        max_length=200,
        blank=True,
    )

    account_number = models.CharField(
        max_length=100,
        blank=True,
    )

    branch_name = models.CharField(
        max_length=200,
        blank=True,
    )

    # =========================================================
    # PAYFAST PAYMENT SETTINGS
    # =========================================================

    payfast_enabled = models.BooleanField(
        default=False,
        help_text="Enable PayFast payments on the website.",
    )

    payfast_merchant_id = models.CharField(
        max_length=150,
        blank=True,
        help_text="Your PayFast Merchant ID.",
    )

    payfast_merchant_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your PayFast Merchant Key.",
    )

    payfast_passphrase = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your PayFast integration passphrase.",
    )

    payfast_sandbox = models.BooleanField(
        default=True,
        help_text="Enable PayFast sandbox mode for testing.",
    )

    # =========================================================
    # PAYPAL PAYMENT SETTINGS
    # =========================================================

    paypal_enabled = models.BooleanField(
        default=False,
        help_text="Enable PayPal payments on the website.",
    )

    paypal_email = models.EmailField(
        blank=True,
        help_text="Your PayPal Business Account email address.",
    )

    paypal_client_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your PayPal REST API Client ID.",
    )

    paypal_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your PayPal REST API Secret.",
    )

    paypal_sandbox = models.BooleanField(
        default=True,
        help_text="Enable PayPal sandbox mode for testing.",
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

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # MODEL META
    # =========================================================

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.business_name

    # =========================================================
    # SAVE SETTINGS
    # =========================================================

    def save(self, *args, **kwargs):
        # Always use one settings record
        self.pk = 1
        super().save(*args, **kwargs)

    # =========================================================
    # LOAD SITE SETTINGS
    # =========================================================

    @classmethod
    def load(cls):
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "business_name": "Hands-On Health",
            },
        )

        return settings