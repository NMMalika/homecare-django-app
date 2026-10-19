
from django.conf import settings
from django.db import models


class QuestionFormSettings(models.Model):
    """Content and topics displayed on the public question form."""

    title = models.CharField(
        max_length=200,
        default="Ask Us Anything",
    )
    badge_text = models.CharField(
        max_length=100,
        default="Still Have Questions?",
    )
    description = models.TextField(
        default=(
            "Can't find the answer you're looking for in our FAQs? "
            "Submit your question below, and our care coordinators "
            "will respond promptly."
        ),
    )
    submit_button_text = models.CharField(
        max_length=100,
        default="Send Question",
    )
    topics = models.JSONField(
        default=list,
        help_text=(
            "Enter a list of topics, each with a label and value."
        ),
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ask a Question Page Settings"
        verbose_name_plural = "Ask a Question Page Settings"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "title": "Ask Us Anything",
                "badge_text": "Still Have Questions?",
                "submit_button_text": "Send Question",
                "topics": [
                    {"value": "care-plans", "label": "Care Plans & Rates"},
                    {"value": "nursing", "label": "Nursing Qualifications"},
                    {"value": "medical-aid", "label": "Medical Aid & Billing"},
                    {"value": "general", "label": "General Enquiry"},
                ],
            },
        )
        return obj


class CustomerQuestion(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        REPLIED = "REPLIED", "Replied"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    topic = models.CharField(
        max_length=100,
        default="general",
    )
    question = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    staff_reply = models.TextField(blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_question_replies",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Customer Question"
        verbose_name_plural = "Customer Questions"

    def __str__(self):
        return f"{self.name} — {self.topic}"
    
class FAQItem(models.Model):
    """Frequently asked questions displayed on the public website."""

    question = models.CharField(max_length=300)
    answer = models.TextField()
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Frequently Asked Question"
        verbose_name_plural = "Frequently Asked Questions"

    def __str__(self):
        return self.question
