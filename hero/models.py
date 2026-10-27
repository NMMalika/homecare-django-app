
from django.db import models


class HeroSlide(models.Model):
    POSITION_CHOICES = [
        (1, "Slide 1"),
        (2, "Slide 2"),
        (3, "Slide 3"),
    ]

    position = models.PositiveSmallIntegerField(
        choices=POSITION_CHOICES,
        unique=True,
    )
    tagline = models.CharField(max_length=200, blank=True)
    heading = models.CharField(max_length=250)
    description = models.TextField()
    image = models.ImageField(
        upload_to="hero/slides/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        verbose_name = "Hero Slide"
        verbose_name_plural = "Hero Slides"

    def __str__(self):
        return f"Slide {self.position}: {self.heading}"
