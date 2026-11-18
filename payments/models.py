from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel
from tenants.models import Tenant
from rent.models import RentCharge
class Payment(TimeStampedModel):
    STATUS=[("PENDING","Pending"),("VERIFIED","Verified"),("REJECTED","Rejected"),("REVERSED","Reversed")]
    METHOD=[("BANK_TRANSFER","Bank transfer"),("MANUAL_BANK","Manual bank reconciliation")]
    tenant=models.ForeignKey(Tenant,on_delete=models.PROTECT,related_name="payments")
    amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0.01)])
    method=models.CharField(max_length=30,choices=METHOD,default="BANK_TRANSFER")
    bank_reference=models.CharField(max_length=120,unique=True)
    payment_date=models.DateTimeField(null=True,blank=True)
    status=models.CharField(max_length=20,choices=STATUS,default="PENDING")
    verified_at=models.DateTimeField(null=True,blank=True)
    verified_by=models.ForeignKey("auth.User",null=True,blank=True,on_delete=models.PROTECT)
    source_note=models.CharField(max_length=255,blank=True)
    def __str__(self): return f"{self.bank_reference} - {self.amount}"
class PaymentAllocation(TimeStampedModel):
    payment=models.ForeignKey(Payment,on_delete=models.PROTECT,related_name="allocations")
    rent_charge=models.ForeignKey(RentCharge,on_delete=models.PROTECT,related_name="allocations")
    allocated_amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0.01)])
    class Meta: constraints=[models.UniqueConstraint(fields=["payment","rent_charge"],name="unique_payment_charge_allocation")]
class BankTransaction(TimeStampedModel):
    bank_name=models.CharField(max_length=80,default="Equity Bank Uganda")
    bank_reference=models.CharField(max_length=120,unique=True)
    transaction_date=models.DateTimeField()
    amount=models.DecimalField(max_digits=14,decimal_places=2)
    narrative=models.CharField(max_length=255,blank=True)
    matched_payment=models.OneToOneField(Payment,null=True,blank=True,on_delete=models.PROTECT)
    reconciliation_status=models.CharField(max_length=20,default="UNMATCHED")
