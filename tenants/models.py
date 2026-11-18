from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator
from core.models import TimeStampedModel
from properties.models import Unit
class Tenant(TimeStampedModel):
    full_name=models.CharField(max_length=160)
    phone=models.CharField(max_length=30)
    email=models.EmailField(blank=True)
    identification_reference=models.CharField(max_length=100,blank=True)
    emergency_contact=models.CharField(max_length=160,blank=True)
    notes=models.TextField(blank=True)
    def __str__(self): return self.full_name
class Tenancy(TimeStampedModel):
    STATUS=[("ACTIVE","Active"),("ENDED","Ended"),("PENDING","Pending")]
    tenant=models.ForeignKey(Tenant,on_delete=models.PROTECT,related_name="tenancies")
    unit=models.ForeignKey(Unit,on_delete=models.PROTECT,related_name="tenancies")
    start_date=models.DateField()
    end_date=models.DateField(null=True,blank=True)
    monthly_rent=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    deposit_amount=models.DecimalField(max_digits=14,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    due_day=models.PositiveSmallIntegerField(default=5,validators=[MinValueValidator(1),MaxValueValidator(28)])
    status=models.CharField(max_length=20,choices=STATUS,default="ACTIVE")
    agreement_file=models.FileField(upload_to="agreements/",blank=True)
    class Meta: indexes=[models.Index(fields=["status","start_date"])]
    def __str__(self): return f"{self.tenant} - {self.unit}"
