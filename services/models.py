# services/models.py
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class ServiceCategory(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    icon_class = models.CharField(
        max_length=50,
        default="fa-solid fa-user-nurse",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name="services",
        null=True,  # Prevent default prompt for existing rows
        blank=True,
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)

    # Base price setup
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    icon_class = models.CharField(
        max_length=50,
        default="fa-solid fa-heart-pulse",
    )
    image = models.ImageField(upload_to="services/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Service"
        verbose_name_plural = "Services"

    @property
    def formatted_price(self):
        return f"N$ {self.price:,.2f}"

    def __str__(self):
        return f"{self.name} ({self.formatted_price})"