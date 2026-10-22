from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Testimonial(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    # Reviewer information
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    photo = models.ImageField(
        upload_to="testimonials/",
        blank=True,
        null=True,
    )

    # Testimonial content
    rating = models.PositiveSmallIntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )
    message = models.TextField()

    # Publication and moderation
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    consent_to_publish = models.BooleanField(default=False)
    staff_notes = models.TextField(blank=True)

    # Optional link to an authenticated reviewer
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_testimonials",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-approved_at", "-created_at"]
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"

    def __str__(self):
        reviewer = "Anonymous" if self.is_anonymous else self.name
        return f"{reviewer} — {self.rating}/5"

    def approve(self):
        """Approve a testimonial for publication."""
        self.status = self.Status.APPROVED
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_at", "updated_at"])

    def reject(self):
        """Reject a testimonial."""
        self.status = self.Status.REJECTED
        self.approved_at = None
        self.save(update_fields=["status", "approved_at", "updated_at"])
