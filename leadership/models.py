from django.db import models


class Founder(models.Model):

    name = models.CharField(
        max_length=200,
        default="Jacobine Joseph",
    )

    position = models.CharField(
        max_length=200,
        default="CEO & Director",
    )

    qualification = models.CharField(
        max_length=200,
        default="Enrolled Nurse",
    )

    photo = models.ImageField(
        upload_to="leadership/founder/",
        blank=True,
        null=True,
    )

    biography_1 = models.TextField(blank=True)
    biography_2 = models.TextField(blank=True)
    biography_3 = models.TextField(blank=True)

    pillar_1 = models.CharField(
        max_length=150,
        default="Dignity-First Care",
    )

    pillar_2 = models.CharField(
        max_length=150,
        default="Clinical Reliability",
    )

    pillar_3 = models.CharField(
        max_length=150,
        default="In-Home Comfort",
    )

    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Founder & Director"
        verbose_name_plural = "Founder & Director"

    def __str__(self):
        return self.name