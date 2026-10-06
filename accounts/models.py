from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Hands-On Health Admin"
        ASSISTANT = "ASSISTANT", "Assistant"
        CAREGIVER = "CAREGIVER", "Caregiver"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ASSISTANT,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True
    )

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    @property
    def is_assistant(self):
        return self.role == self.Role.ASSISTANT

    @property
    def is_caregiver(self):
        return self.role == self.Role.CAREGIVER

    def save(self, *args, **kwargs):

        if self.role in (
            self.Role.SUPER_ADMIN,
            self.Role.ADMIN,
        ):
            self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username