from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel


class Landlord(TimeStampedModel):
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    postal_address = models.CharField(max_length=255, blank=True)
    tax_reference = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.full_name


class Property(TimeStampedModel):
    STATUS = [("ACTIVE", "Active"), ("INACTIVE", "Inactive")]
    landlord = models.ForeignKey(Landlord, on_delete=models.PROTECT, related_name="properties")
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="ACTIVE")

    def __str__(self):
        return self.name


class PropertyAssignment(TimeStampedModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="assignments")
    staff = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="property_assignments")

    class Meta:
        unique_together = ("property", "staff")

    def __str__(self):
        return f"{self.staff} - {self.property}"


class Unit(TimeStampedModel):
    STATUS = [
        ("VACANT", "Vacant"),
        ("OCCUPIED", "Occupied"),
        ("MAINTENANCE", "Under maintenance"),
        ("INACTIVE", "Inactive"),
        ("PENDING_VERIFICATION", "Pending verification"),
    ]
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="units")
    unit_number = models.CharField(max_length=40)
    monthly_rent = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=24, choices=STATUS, default="VACANT")
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("property", "unit_number")
        ordering = ("property__name", "unit_number")

    def __str__(self):
        return f"{self.property.name} / {self.unit_number}"
