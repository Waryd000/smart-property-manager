from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel
from tenants.models import Tenancy
class RentCharge(TimeStampedModel):
    STATUS=[("UNPAID","Unpaid"),("PARTIAL","Partially paid"),("PAID","Paid"),("OVERDUE","Overdue"),("CREDIT","Overpaid")]
    tenancy=models.ForeignKey(Tenancy,on_delete=models.PROTECT,related_name="rent_charges")
    billing_month=models.DateField(help_text="Use the first day of the billing month")
    amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    due_date=models.DateField()
    status=models.CharField(max_length=20,choices=STATUS,default="UNPAID")
    class Meta: unique_together=("tenancy","billing_month"); ordering=("due_date",)
    @property
    def amount_paid(self):
        return self.allocations.filter(reversed_at__isnull=True).aggregate(
            v=models.Sum("allocated_amount")
        )["v"] or Decimal("0.00")
    @property
    def balance(self): return self.amount-self.amount_paid
    def refresh_status(self):
        from django.utils import timezone
        if self.balance <= 0: self.status="PAID" if self.balance == 0 else "CREDIT"
        elif self.amount_paid > 0: self.status="PARTIAL"
        elif self.due_date < timezone.localdate(): self.status="OVERDUE"
        else: self.status="UNPAID"
        self.save(update_fields=["status","updated_at"])
class ManagementFee(TimeStampedModel):
    STATUS=[("DUE","Due"),("PAID","Paid"),("WAIVED","Waived")]
    property=models.ForeignKey("properties.Property",on_delete=models.PROTECT,related_name="management_fees")
    billing_month=models.DateField()
    amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    due_date=models.DateField()
    status=models.CharField(max_length=20,choices=STATUS,default="DUE")
    notes=models.TextField(blank=True)
    class Meta: unique_together=("property","billing_month")
