from django.db import models


class ChatbotKnowledge(models.Model):
    class Category(models.TextChoices):
        ABOUT = "about", "About Us"
        CAREERS = "careers", "Careers / Joining"
        PAYMENT = "payment", "Payment Information"
        REFERRAL = "referral", "Referrals"
        SERVICES = "services", "Services"
        POLICY = "policy", "Policies"
        GENERAL = "general", "General"

    title = models.CharField(max_length=220)
    answer = models.TextField(
        help_text="Public information only. Never enter patient or staff private details."
    )
    keywords = models.TextField(
        blank=True,
        help_text="Alternative questions or search phrases, separated by commas.",
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL
    )
    is_published = models.BooleanField(default=False)
    priority = models.PositiveSmallIntegerField(
        default=0, help_text="Higher priority wins close matches."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "-updated_at"]
        verbose_name = "Chatbot knowledge article"
        verbose_name_plural = "Chatbot knowledge articles"

    def __str__(self):
        return self.title

class UnansweredQuestion(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        REVIEWED = "REVIEWED", "Reviewed"
        RESOLVED = "RESOLVED", "Resolved"
        IGNORED = "IGNORED", "Ignored"

    question = models.TextField()
    normalized_question = models.CharField(max_length=500, db_index=True)
    occurrences = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    last_asked_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_asked_at"]

    def __str__(self):
        return self.question[:100]


class ChatbotConversationLog(models.Model):

    class ReviewStatus(models.TextChoices):
        UNREVIEWED = "UNREVIEWED", "Not Reviewed"
        CORRECT = "CORRECT", "Answer Correct"
        INCORRECT = "INCORRECT", "Needs Correction"
        TRAINED = "TRAINED", "Training Completed"

    question = models.TextField(max_length=500)
    chatbot_answer = models.TextField()
    answer_source = models.CharField(
        max_length=60,
        default="general",
    )
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.UNREVIEWED,
        db_index=True,
    )
    staff_answer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:100]
