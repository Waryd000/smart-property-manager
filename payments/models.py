from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.models import TimeStampedModel
from properties.models import Property
from tenants.models import Tenant
from rent.models import RentCharge


class Payment(TimeStampedModel):
    STATUS = [
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("REJECTED", "Rejected"),
        ("REVERSED", "Reversed"),
    ]
    METHOD = [
        ("BANK_TRANSFER", "Bank transfer"),
        ("MANUAL_BANK", "Manual bank reconciliation"),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="payments")
    # The receiving property is mandatory for verification and allocation.
    # Nullable only so historical/unclassified records can be reviewed safely.
    property = models.ForeignKey(
        Property,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0.01)])
    unallocated_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Verified payment funds not yet allocated to rent charges.",
    )
    method = models.CharField(max_length=30, choices=METHOD, default="BANK_TRANSFER")
    bank_reference = models.CharField(max_length=120, unique=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.PROTECT)
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.PROTECT,
        related_name="reversed_payments",
    )
    reversal_reason = models.TextField(blank=True)
    source_note = models.CharField(max_length=255, blank=True)

    def clean(self):
        super().clean()
        errors = {}
        if self.status == "VERIFIED":
            if not self.property_id:
                errors["property"] = "A verified payment must be linked to a property."
            bank_transaction = BankTransaction.objects.filter(
                bank_reference=self.bank_reference
            ).first()
            if bank_transaction is None:
                errors["bank_reference"] = (
                    "A verified payment must match an imported bank transaction."
                )
            else:
                if bank_transaction.amount != self.amount:
                    errors["amount"] = (
                        "The payment amount must match the imported bank transaction."
                    )
                if (
                    self.payment_date
                    and timezone.localdate(self.payment_date)
                    != timezone.localdate(bank_transaction.transaction_date)
                ):
                    errors["payment_date"] = (
                        "The payment date must match the bank transaction date."
                    )
                if (
                    bank_transaction.matched_payment_id is not None
                    and bank_transaction.matched_payment_id != self.pk
                ):
                    errors["bank_reference"] = (
                        "This bank transaction is already matched to another payment."
                    )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.bank_reference} - {self.amount}"


class PaymentAllocation(TimeStampedModel):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="allocations")
    rent_charge = models.ForeignKey(RentCharge, on_delete=models.PROTECT, related_name="allocations")
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0.01)])
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.PROTECT,
        related_name="reversed_payment_allocations",
    )
    reversal_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "rent_charge"],
                name="unique_payment_charge_allocation",
            )
        ]


class BankTransaction(TimeStampedModel):
    bank_name = models.CharField(max_length=80, default="Equity Bank Uganda")
    bank_reference = models.CharField(max_length=120, unique=True)
    transaction_date = models.DateTimeField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    narrative = models.CharField(max_length=255, blank=True)
    matched_payment = models.OneToOneField(
        Payment,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    reconciliation_status = models.CharField(max_length=20, default="UNMATCHED")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="bank_transaction_amount_positive",
            )
        ]
