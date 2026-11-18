from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel
from properties.models import Property,Unit
class UtilityBill(TimeStampedModel):
    TYPES=[("WATER","Water"),("ELECTRICITY","Electricity"),("OTHER","Other")]
    PAYER=[("LANDLORD","Landlord"),("TENANT","Tenant"),("MANAGER","Manager")]
    property=models.ForeignKey(Property,on_delete=models.PROTECT,related_name="utility_bills")
    unit=models.ForeignKey(Unit,null=True,blank=True,on_delete=models.PROTECT)
    utility_type=models.CharField(max_length=20,choices=TYPES)
    payer=models.CharField(max_length=20,choices=PAYER,default="LANDLORD")
    account_or_meter_number=models.CharField(max_length=100,blank=True)
    billing_period=models.DateField()
    amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    due_date=models.DateField()
    paid_at=models.DateTimeField(null=True,blank=True)
    status=models.CharField(max_length=20,default="PENDING")
    reference=models.CharField(max_length=100,blank=True)
class MaintenanceRequest(TimeStampedModel):
    PRIORITY=[("LOW","Low"),("NORMAL","Normal"),("HIGH","High"),("URGENT","Urgent")]
    STATUS=[("OPEN","Open"),("REVIEW","Under review"),("APPROVED","Approved"),("IN_PROGRESS","In progress"),("COMPLETED","Completed"),("CANCELLED","Cancelled")]
    property=models.ForeignKey(Property,on_delete=models.PROTECT,related_name="maintenance_requests")
    unit=models.ForeignKey(Unit,null=True,blank=True,on_delete=models.PROTECT)
    reported_by=models.CharField(max_length=150,blank=True)
    description=models.TextField()
    priority=models.CharField(max_length=20,choices=PRIORITY,default="NORMAL")
    status=models.CharField(max_length=20,choices=STATUS,default="OPEN")
    estimated_cost=models.DecimalField(max_digits=14,decimal_places=2,null=True,blank=True)
    actual_cost=models.DecimalField(max_digits=14,decimal_places=2,null=True,blank=True)
    assigned_to=models.ForeignKey("auth.User",null=True,blank=True,on_delete=models.PROTECT)
    completed_at=models.DateTimeField(null=True,blank=True)
class Expense(TimeStampedModel):
    STATUS=[("PENDING","Pending approval"),("APPROVED","Approved"),("PAID","Paid"),("REJECTED","Rejected")]
    property=models.ForeignKey(Property,on_delete=models.PROTECT,related_name="expenses")
    category=models.CharField(max_length=100)
    description=models.CharField(max_length=255)
    amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    incurred_on=models.DateField()
    status=models.CharField(max_length=20,choices=STATUS,default="PENDING")
    approved_by=models.ForeignKey("auth.User",null=True,blank=True,on_delete=models.PROTECT,related_name="approved_expenses")
class AuditLog(TimeStampedModel):
    user=models.ForeignKey("auth.User",null=True,blank=True,on_delete=models.SET_NULL)
    action=models.CharField(max_length=100)
    model_name=models.CharField(max_length=100)
    record_id=models.CharField(max_length=80,blank=True)
    details=models.JSONField(default=dict,blank=True)
    ip_address=models.GenericIPAddressField(null=True,blank=True)
