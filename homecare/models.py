import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


# ============================================================
# TOKEN / ROOM GENERATORS
# ============================================================

def generate_quotation_token():
    return secrets.token_urlsafe(32)


def generate_access_token():
    return secrets.token_urlsafe(48)


def generate_room_name():
    return f"hands-on-health-{uuid.uuid4().hex}"


def generate_booking_token():
    """
    Secure public token used by the patient to access
    their appointment availability without logging in.
    """
    return secrets.token_urlsafe(48)


# ============================================================
# HOME CARE REQUEST
# ============================================================

class HomeCareRequest(models.Model):

    class Status(models.TextChoices):
        NEW = "NEW", "New Request"
        CONTACTED = "CONTACTED", "Contacted"
        QUOTED = "QUOTED", "Quotation Sent"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        PAYMENT_RECEIVED = "PAYMENT_RECEIVED", "Payment Received"
        CONFIRMED = "CONFIRMED", "Confirmed"
        ASSIGNED = "ASSIGNED", "Caregiver Assigned"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    full_name = models.CharField(
        max_length=200
    )

    phone = models.CharField(
        max_length=50
    )

    email = models.EmailField()

    location = models.CharField(
        max_length=255
    )

    services = models.ManyToManyField(
        "services.Service",
        related_name="home_care_requests",
        blank=True,
    )

    preferred_date = models.DateField()

    preferred_time = models.TimeField()

    description = models.TextField(
        help_text="Describe the care or support required."
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW,
    )

    admin_notes = models.TextField(
        blank=True
    )

    contacted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_reason = models.TextField(
        blank=True
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} - Request #{self.id}"


# ============================================================
# HOME CARE REQUEST ATTACHMENTS
# ============================================================

class HomeCareRequestAttachment(models.Model):

    homecare_request = models.ForeignKey(
        HomeCareRequest,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="homecare/attachments/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Attachment #{self.id} "
            f"for Request #{self.homecare_request.id}"
        )


# ============================================================
# REFERRAL
# ============================================================

class Referral(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending Payment")
        COMPLETED = "COMPLETED", _("Completed & Paid")

    referrer_name = models.CharField(
        max_length=255
    )

    referrer_email = models.EmailField()

    referrer_phone = models.CharField(
        max_length=50
    )

    referring_facility = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Name of hospital, clinic, or institution "
            "(if applicable)."
        ),
    )

    patient_name = models.CharField(
        max_length=255
    )

    patient_email = models.EmailField()

    patient_phone = models.CharField(
        max_length=50
    )
    
    location = models.CharField(max_length=255, help_text="Patient's location or address")
    
    services_needed = models.ManyToManyField(
        "services.Service",
        related_name="referrals",
        blank=True,
    )

    additional_notes = models.TextField(
        blank=True
    )

    homecare_request = models.OneToOneField(
        HomeCareRequest,
        on_delete=models.SET_NULL,
        related_name="referral_source",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    loyalty_points_awarded = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Points awarded to the referrer "
            "after patient payment."
        ),
    )

    thanked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Timestamp when the thank-you email/SMS "
            "was dispatched."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Referral by {self.referrer_name} "
            f"for {self.patient_name}"
        )


# ============================================================
# REFERRAL ATTACHMENTS
# ============================================================

class ReferralAttachment(models.Model):

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="referrals/attachments/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Attachment #{self.id} "
            f"for Referral #{self.referral.id}"
        )


# ============================================================
# CONSULTATION / BOOK APPOINTMENT
# ============================================================

class Consultation(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        QUOTED = "QUOTED", "Quote Sent"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        PAID = "PAID", "Paid"
        SCHEDULED = "SCHEDULED", "Scheduled"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    first_name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=100
    )

    email = models.EmailField()

    phone = models.CharField(
        max_length=30
    )

    services = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Services selected by the patient "
            "during appointment booking."
        ),
    )

    requested_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date requested by the patient.",
    )

    requested_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time requested by the patient.",
    )

    message = models.TextField(
        blank=True,
        help_text=(
            "Additional information provided "
            "by the patient."
        ),
    )

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultations",
        null=True,
        blank=True,
        help_text="Doctor conducting the consultation.",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    consultation_date = models.DateField(
        null=True,
        blank=True,
        help_text="Confirmed consultation date.",
    )

    consultation_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Confirmed consultation time.",
    )

    duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Expected consultation duration.",
    )

    booking_token = models.CharField(
        max_length=128,
        unique=True,
        default=generate_booking_token,
        editable=False,
        help_text=(
            "Secure token used by the patient to access "
            "appointment availability."
        ),
    )

    room_name = models.CharField(
        max_length=255,
        default=generate_room_name,
        unique=True,
        editable=False,
    )

    patient_access_token = models.CharField(
        max_length=128,
        default=generate_access_token,
        unique=True,
        editable=False,
    )

    doctor_access_token = models.CharField(
        max_length=128,
        default=generate_access_token,
        unique=True,
        editable=False,
    )

    patient_join_url = models.URLField(
        blank=True,
        help_text="Secure patient telemedicine URL.",
    )

    doctor_join_url = models.URLField(
        blank=True,
        help_text="Secure doctor telemedicine URL.",
    )

    admin_notes = models.TextField(
        blank=True,
    )

    doctor_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.first_name} {self.last_name} "
            f"- Appointment #{self.id}"
        )


# ============================================================
# CONSULTATION AVAILABLE SLOTS
# ============================================================

class ConsultationSlot(models.Model):

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="available_slots",
        help_text="Consultation this slot belongs to.",
    )

    date = models.DateField(
        help_text="Available consultation date.",
    )

    time = models.TimeField(
        help_text="Available consultation time.",
    )

    duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Expected consultation duration.",
    )

    is_available = models.BooleanField(
        default=True,
        help_text=(
            "Whether this slot is currently available "
            "for the patient to select."
        ),
    )

    is_selected = models.BooleanField(
        default=False,
        help_text=(
            "Indicates that the patient selected "
            "this appointment slot."
        ),
    )

    selected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the patient selected this slot.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "date",
            "time",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "consultation",
                    "date",
                    "time",
                ],
                name="unique_consultation_slot",
            ),
        ]

    def __str__(self):
        return (
            f"{self.consultation.first_name} "
            f"{self.consultation.last_name} - "
            f"{self.date} {self.time}"
        )


# ============================================================
# CONSULTATION ATTACHMENTS
# ============================================================

class ConsultationAttachment(models.Model):

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="consultations/attachments/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Attachment #{self.id} "
            f"for Appointment #{self.consultation.id}"
        )


# ============================================================
# QUOTATION
# ============================================================

class Quotation(models.Model):

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Payment Pending"
        PAID = "PAID", "Paid"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    # ========================================================
    # RELATED REQUEST / CONSULTATION
    # ========================================================

    homecare_request = models.OneToOneField(
        HomeCareRequest,
        on_delete=models.CASCADE,
        related_name="quotation",
        null=True,
        blank=True,
    )

    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name="quotation",
        null=True,
        blank=True,
    )

    # ========================================================
    # QUOTATION TOTALS
    # ========================================================

    base_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=(
            "Total cost of all quotation service items "
            "before transport and discount."
        ),
    )

    transportation_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=(
            "Additional transportation charges. "
            "Usually applicable to home care."
        ),
    )

    discount_code = models.CharField(
        max_length=50,
        blank=True,
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Final amount payable by the patient.",
    )

    # ========================================================
    # DESCRIPTION
    # ========================================================

    description = models.TextField(
        blank=True,
        help_text="Additional quotation notes and payment instructions.",
    )

    # ========================================================
    # PAYMENT
    # ========================================================

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    # ========================================================
    # SECURE ACCESS
    # ========================================================

    access_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_quotation_token,
        editable=False,
    )

    # ========================================================
    # DATES
    # ========================================================

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    payment_deadline = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        if self.homecare_request and self.consultation:
            raise ValidationError(
                "A quotation cannot belong to both "
                "a Home Care Request and a Consultation."
            )

        if not self.homecare_request and not self.consultation:
            raise ValidationError(
                "A quotation must belong to either "
                "a Home Care Request or a Consultation."
            )

    # ========================================================
    # CALCULATE ITEMS TOTAL
    # ========================================================

    def calculate_items_total(self):

        total = sum(
            (
                item.line_total
                for item in self.items.all()
            ),
            Decimal("0.00"),
        )

        return total

    # ========================================================
    # CALCULATE FINAL TOTAL
    # ========================================================

    def calculate_total(self):

        items_total = self.calculate_items_total()

        total = (
            items_total
            + self.transportation_fee
            - self.discount_amount
        )

        return max(
            total,
            Decimal("0.00"),
        )

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):

        # ----------------------------------------------------
        # Only calculate automatically when the quotation
        # already has a primary key and therefore can have
        # quotation items.
        # ----------------------------------------------------

        if self.pk:

            try:
                self.base_amount = (
                    self.calculate_items_total()
                )

                self.amount = (
                    self.calculate_total()
                )

            except Exception:
                pass

        super().save(*args, **kwargs)

    # ========================================================
    # STRING
    # ========================================================

    def __str__(self):

        if self.consultation:
            return (
                f"Quotation - "
                f"{self.consultation.first_name} "
                f"{self.consultation.last_name} "
                f"(Appointment)"
            )

        if self.homecare_request:
            return (
                f"Quotation - "
                f"{self.homecare_request.full_name} "
                f"(Home Care)"
            )

        return f"Quotation #{self.id}"


# ============================================================
# QUOTATION ITEM
# ============================================================

class QuotationItem(models.Model):
    """
    Individual item/service appearing on a quotation.

    A quotation can have unlimited quotation items.

    Items may come from:
        1. Existing Services in the Services database
        2. Manually added services by staff

    Examples:

        Nursing Care              N$ 500
        Medication Administration N$ 250
        Wound Dressing            N$ 300
        Transport                 N$ 150
        Special Equipment         N$ 200
        Custom Service            N$ 400
    """

    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="items",
    )

    # ========================================================
    # EXISTING SERVICE
    # ========================================================

    service = models.ForeignKey(
        "services.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotation_items",
        help_text=(
            "Optional existing service from the Services database."
        ),
    )

    # ========================================================
    # SERVICE NAME
    # ========================================================

    name = models.CharField(
        max_length=255,
        help_text="Name of the service/item shown on the quotation.",
    )

    # ========================================================
    # DESCRIPTION
    # ========================================================

    description = models.TextField(
        blank=True,
        help_text="Optional description of this service/item.",
    )

    # ========================================================
    # QUANTITY
    # ========================================================

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
    )

    # ========================================================
    # UNIT PRICE
    # ========================================================

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ========================================================
    # LINE TOTAL
    # ========================================================

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    # ========================================================
    # ORDER
    # ========================================================

    order = models.PositiveIntegerField(
        default=0,
    )

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "order",
            "id",
        ]

    # ========================================================
    # CALCULATE LINE TOTAL
    # ========================================================

    def calculate_total(self):

        return (
            self.quantity * self.unit_price
        )

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):

        # ----------------------------------------------------
        # If linked to an existing service and no custom name
        # has been provided, use the service name.
        # ----------------------------------------------------

        if self.service:

            if not self.name:
                self.name = self.service.name

        # ----------------------------------------------------
        # Automatically calculate line total
        # ----------------------------------------------------

        self.line_total = self.calculate_total()

        super().save(*args, **kwargs)

    # ========================================================
    # STRING
    # ========================================================

    def __str__(self):

        return (
            f"{self.name} × {self.quantity} "
            f"@ N$ {self.unit_price:,.2f}"
        )
# ============================================================
# PAYMENT
# ============================================================

class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting Verification"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    class PaymentMethod(models.TextChoices):
        BANK = "BANK", "Bank Transfer"
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
        OTHER = "OTHER", "Other"

    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    payment_code = models.CharField(
        max_length=150,
        help_text=(
            "Transaction/reference code "
            "provided by the client."
        ),
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount the client claims to have paid.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_homecare_payments",
    )

    admin_notes = models.TextField(
        blank=True,
    )

    def __str__(self):

        if self.quotation.consultation:

            patient = (
                f"{self.quotation.consultation.first_name} "
                f"{self.quotation.consultation.last_name}"
            )

        elif self.quotation.homecare_request:

            patient = (
                self.quotation.homecare_request.full_name
            )

        else:

            patient = "Unknown Client"

        return (
            f"{patient} - "
            f"{self.payment_code}"
        )

    class Meta:
        ordering = ["-submitted_at"]


# ============================================================
# CAREGIVER
# ============================================================

class Caregiver(models.Model):

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Verification"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        SUSPENDED = "SUSPENDED", "Suspended"

    # ========================================================
    # ACCOUNT
    # ========================================================

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="caregiver_profile",
    )

    # ========================================================
    # PERSONAL / PROFESSIONAL INFORMATION
    # ========================================================

    name = models.CharField(
        max_length=200,
        blank=True,
    )

    professional_title = models.CharField(
        max_length=200,
        blank=True,
    )

    specialization = models.CharField(
        max_length=255,
        blank=True,
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    photo = models.ImageField(
        upload_to="caregivers/",
        blank=True,
        null=True,
    )

    availability = models.TextField(
        blank=True,
    )

    # ========================================================
    # LICENCE
    # ========================================================

    licence_number = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Licence Number",
        help_text="Professional licence/registration number.",
    )

    licence_issuing_authority = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Licence Issuing Authority",
        help_text="Authority or professional body that issued the licence.",
    )

    licence_expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Licence Expiry Date",
    )

    licence_document = models.FileField(
        upload_to="caregivers/licences/",
        blank=True,
        null=True,
        verbose_name="Licence Document",
    )

    # ========================================================
    # APPLICATION DOCUMENTS
    # ========================================================

    cv = models.FileField(
        upload_to="caregivers/cv/",
        blank=True,
        null=True,
        verbose_name="CV / Resume",
    )

    cover_letter = models.FileField(
        upload_to="caregivers/cover_letters/",
        blank=True,
        null=True,
        verbose_name="Cover Letter",
    )

    # ========================================================
    # VERIFICATION
    # ========================================================

    certificate_submitted = models.BooleanField(
        default=False,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    verification_notes = models.TextField(
        blank=True,
        verbose_name="Verification Comment",
        help_text=(
            "Admin comment explaining approval, rejection, "
            "or missing documents."
        ),
    )

    verification_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verification_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_caregiver_applications",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_caregivers",
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_caregivers",
    )

    # ========================================================
    # ACTIVE STATUS
    # ========================================================

    is_active = models.BooleanField(
        default=False,
    )

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):

        # ----------------------------------------------------
        # Automatically populate caregiver name/email from
        # the registered User account.
        # ----------------------------------------------------

        if self.user:

            full_name = self.user.get_full_name().strip()

            if not self.name:

                if full_name:
                    self.name = full_name

                elif self.user.username:
                    self.name = self.user.username

            if not self.email and self.user.email:
                self.email = self.user.email

        # ----------------------------------------------------
        # Keep inactive while not approved.
        # ----------------------------------------------------

        if self.verification_status != self.VerificationStatus.APPROVED:
            self.is_active = False

        super().save(*args, **kwargs)

    def __str__(self):

        if self.name:
            return (
                f"{self.name} - "
                f"{self.professional_title or 'Caregiver'}"
            )

        if self.user:
            return (
                f"{self.user.get_full_name() or self.user.username} "
                f"- Caregiver"
            )

        return f"Caregiver #{self.id}"


# ============================================================
# CAREGIVER ASSIGNMENT
# ============================================================

class CaregiverAssignment(models.Model):

    class Duration(models.TextChoices):
        ONE_DAY = "ONE_DAY", "One Day"
        ONE_WEEK = "ONE_WEEK", "One Week"

    class ReportFrequency(models.TextChoices):
        DAILY = "DAILY", "Daily Reports"
        WEEKLY = "WEEKLY", "Weekly Report"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Acceptance"
        ACCEPTED = "ACCEPTED", "Accepted"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        DECLINED = "DECLINED", "Declined"
        CANCELLED = "CANCELLED", "Cancelled"

    homecare_request = models.OneToOneField(
        HomeCareRequest,
        on_delete=models.CASCADE,
        related_name="caregiver_assignment",
    )

    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    duration = models.CharField(
        max_length=20,
        choices=Duration.choices,
        default=Duration.ONE_DAY,
        help_text="Whether this assignment is for one day or one week.",
    )

    start_date = models.DateField(null=True, blank=True,
        help_text="First day of the caregiver assignment.",
    )

    end_date = models.DateField(null=True, blank=True,
        help_text="Last day of the caregiver assignment.",
    )

    # Kept for compatibility with the existing assignment code.
    service_date = models.DateField(
        null=True,
        blank=True,
        help_text="Specific/legacy service date. Normally use start_date.",
    )

    service_time = models.TimeField(
        null=True,
        blank=True,
    )

    report_frequency = models.CharField(
        max_length=20,
        choices=ReportFrequency.choices,
        default=ReportFrequency.DAILY,
        help_text="How the caregiver should submit reports.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    declined_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    caregiver_response_note = models.TextField(
        blank=True,
        help_text="Optional note entered by the caregiver when accepting or declining.",
    )

    notes = models.TextField(
        blank=True,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="homecare_caregiver_assignments",
    )

    class Meta:
        ordering = ["-assigned_at"]

    def clean(self):
        super().clean()

        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError(
                    "Assignment end date cannot be before the start date."
                )

            if self.duration == self.Duration.ONE_DAY:
                if self.start_date != self.end_date:
                    raise ValidationError(
                        "A one-day assignment must have the same start and end date."
                    )

            elif self.duration == self.Duration.ONE_WEEK:
                days = (self.end_date - self.start_date).days + 1
                if days != 7:
                    raise ValidationError(
                        "A one-week assignment must cover exactly 7 days."
                    )

    @property
    def total_days(self):
        if not self.start_date or not self.end_date:
            return 0
        return (self.end_date - self.start_date).days + 1

    @property
    def is_accepted(self):
        return self.status in {
            self.Status.ACCEPTED,
            self.Status.IN_PROGRESS,
            self.Status.COMPLETED,
        }

    @property
    def is_active(self):
        return self.status in {
            self.Status.ACCEPTED,
            self.Status.IN_PROGRESS,
        }

    def __str__(self):
        return (
            f"{self.caregiver.name} → "
            f"{self.homecare_request.full_name}"
        )

# ============================================================
# CAREGIVER ASSIGNMENT HISTORY
# ============================================================

class CaregiverAssignmentHistory(models.Model):
    """
    Keeps a permanent history of every caregiver assignment,
    acceptance, decline and reassignment.

    This is especially important because a HomeCareRequest has
    only one active CaregiverAssignment record.
    """

    class Action(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Assigned"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        REASSIGNED = "REASSIGNED", "Reassigned"
        STARTED = "STARTED", "Started"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    assignment = models.ForeignKey(
        CaregiverAssignment,
        on_delete=models.CASCADE,
        related_name="history",
    )

    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.PROTECT,
        related_name="assignment_history",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )

    note = models.TextField(
        blank=True,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="caregiver_assignment_history",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.assignment.homecare_request.full_name} - "
            f"{self.caregiver.name} - "
            f"{self.get_action_display()}"
        )
# ============================================================
# CAREGIVER CERTIFICATE
# ============================================================

class CaregiverCertificate(models.Model):

    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.CASCADE,
        related_name="certificates",
    )

    # --------------------------------------------------------
    # NAME GIVEN BY THE CAREGIVER
    # --------------------------------------------------------

    certificate_name = models.CharField(
        max_length=255,
        verbose_name="Certificate Name",
        help_text=(
            "Example: Kenya Registered Community Health Nurse "
            "Certificate"
        ),
    )

    certificate_number = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Certificate Number",
    )

    issuing_organization = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Issuing Organization",
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Issue Date",
    )

    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Expiry Date",
    )

    # --------------------------------------------------------
    # ACTUAL CERTIFICATE FILE
    # --------------------------------------------------------

    document = models.FileField(
        upload_to="caregivers/certificates/",
        verbose_name="Certificate Document",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    # --------------------------------------------------------
    # CERTIFICATE VERIFICATION
    # --------------------------------------------------------

    is_verified = models.BooleanField(
        default=False,
    )

    verification_notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return (
            f"{self.caregiver.name} - "
            f"{self.certificate_name}"
        )


# ============================================================
# CAREGIVER DAILY REPORT
# ============================================================

class CaregiverDailyReport(models.Model):

    class PatientCondition(models.TextChoices):
        STABLE = "STABLE", "Stable"
        IMPROVING = "IMPROVING", "Improving"
        UNCHANGED = "UNCHANGED", "No Significant Change"
        DETERIORATING = "DETERIORATING", "Deteriorating"
        URGENT = "URGENT", "Urgent Attention Required"

    assignment = models.ForeignKey(
        CaregiverAssignment,
        on_delete=models.CASCADE,
        related_name="daily_reports",
    )

    report_date = models.DateField()

    visit_start_time = models.TimeField(
        null=True,
        blank=True
    )

    visit_end_time = models.TimeField(
        null=True,
        blank=True
    )

    patient_condition = models.CharField(
        max_length=20,
        choices=PatientCondition.choices,
        default=PatientCondition.STABLE,
    )

    vital_observations = models.TextField(
        blank=True
    )

    care_provided = models.TextField()

    patient_progress = models.TextField()

    concerns = models.TextField(
        blank=True
    )

    next_visit_date = models.DateField(
        null=True,
        blank=True
    )

    caregiver_notes = models.TextField(
        blank=True
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_caregiver_reports",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = [
            "-report_date",
            "-submitted_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "assignment",
                    "report_date"
                ],
                name="unique_daily_report_per_assignment_date",
            ),
        ]

    def __str__(self):
        return (
            f"{self.assignment.caregiver.name} - "
            f"{self.assignment.homecare_request.full_name} - "
            f"{self.report_date}"
        )


# ============================================================
# CAREGIVER WEEKLY REPORT
# ============================================================

class CaregiverWeeklyReport(models.Model):
    """
    Weekly summary submitted for a caregiver assignment.

    CaregiverDailyReport remains responsible for individual daily
    reports. This model is used when weekly reporting is selected.
    """

    assignment = models.ForeignKey(
        CaregiverAssignment,
        on_delete=models.CASCADE,
        related_name="weekly_reports",
    )

    week_start = models.DateField()
    week_end = models.DateField()

    overall_condition = models.CharField(
        max_length=20,
        choices=CaregiverDailyReport.PatientCondition.choices,
        default=CaregiverDailyReport.PatientCondition.STABLE,
    )

    care_provided = models.TextField()
    patient_progress = models.TextField()

    concerns = models.TextField(
        blank=True,
    )

    recommendations = models.TextField(
        blank=True,
    )

    caregiver_notes = models.TextField(
        blank=True,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_caregiver_weekly_reports",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-week_start", "-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "week_start", "week_end"],
                name="unique_weekly_report_per_assignment_period",
            ),
        ]

    def clean(self):
        super().clean()

        if self.week_start and self.week_end:
            if self.week_end < self.week_start:
                raise ValidationError(
                    "Weekly report end date cannot be before the start date."
                )

            if (self.week_end - self.week_start).days + 1 > 7:
                raise ValidationError(
                    "A weekly report cannot cover more than 7 days."
                )

    def __str__(self):
        return (
            f"{self.assignment.caregiver.name} - "
            f"{self.assignment.homecare_request.full_name} - "
            f"{self.week_start} to {self.week_end}"
        )


# ============================================================
# CAREGIVER PAYMENT
# ============================================================

class CaregiverPayment(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved for Payment"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    assignment = models.ForeignKey(
        CaregiverAssignment,
        on_delete=models.PROTECT,
        related_name="caregiver_payments",
    )

    payment_date = models.DateField(
        null=True,
        blank=True
    )

    service_period_start = models.DateField(
        null=True,
        blank=True
    )

    service_period_end = models.DateField(
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    payment_reference = models.CharField(
        max_length=150,
        blank=True
    )

    payment_method = models.CharField(
        max_length=100,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_caregiver_payments",
    )

    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paid_caregiver_payments",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.caregiver.name} - "
            f"{self.amount} - "
            f"{self.get_status_display()}"
        )
    # ============================================================
# CAREGIVER INVITATION
# ============================================================

class CaregiverInvitation(models.Model):
    """
    Secure one-time invitation allowing a staff member to invite
    a caregiver to complete their account registration.

    The caregiver does not receive a password from staff.
    They create their own password through the invitation link.
    """

    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    email = models.EmailField()

    token = models.CharField(
        max_length=128,
        unique=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="caregiver_invitations_created",
    )

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        from django.utils import timezone

        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def __str__(self):
        return (
            f"Caregiver invitation - "
            f"{self.email}"
        )