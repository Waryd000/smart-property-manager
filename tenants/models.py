from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel
from properties.models import Unit


class Tenant(TimeStampedModel):
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    identification_reference = models.CharField(max_length=100, blank=True)
    emergency_contact = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.full_name


class Tenancy(TimeStampedModel):
    STATUS = [("ACTIVE", "Active"), ("ENDED", "Ended"), ("PENDING", "Pending")]
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="tenancies")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="tenancies")
    # Legacy registers may omit commencement dates. Such records stay pending
    # until the real start date and occupancy have been confirmed.
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    deposit_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    due_day = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(28)])
    status = models.CharField(max_length=20, choices=STATUS, default="ACTIVE")
    agreement_file = models.FileField(upload_to="agreements/", blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "start_date"])]
        constraints = [
            models.UniqueConstraint(
                fields=["unit"],
                condition=Q(status="ACTIVE"),
                name="one_active_tenancy_per_unit",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.status == "ACTIVE" and self.start_date is None:
            errors["start_date"] = (
                "An active tenancy needs a confirmed start date. "
                "Keep the tenancy pending until the date is verified."
            )

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            errors["end_date"] = "The tenancy end date cannot be before its start date."

        if self.status == "ACTIVE" and self.unit_id:
            existing = Tenancy.objects.filter(
                unit_id=self.unit_id,
                status="ACTIVE",
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                errors["unit"] = (
                    "This unit already has an active tenancy. "
                    "End or correct the existing tenancy before creating another."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.tenant} - {self.unit}"
