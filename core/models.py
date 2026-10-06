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

    mobile_money_name = models.CharField(
        max_length=200,
        blank=True,
    )

    mobile_money_number = models.CharField(
        max_length=50,
        blank=True,
    )

    payment_instructions = models.TextField(
        blank=True,
        help_text="Additional instructions shown to clients on quotations.",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        # Always use one settings record
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