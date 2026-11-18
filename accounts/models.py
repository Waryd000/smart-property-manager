from django.contrib.auth.models import User
from django.db import models
from core.models import TimeStampedModel
class StaffProfile(TimeStampedModel):
    ROLE_CHOICES=[("MANAGER","Manager"),("STAFF","Staff")]
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name="staff_profile")
    phone=models.CharField(max_length=30,blank=True)
    role=models.CharField(max_length=20,choices=ROLE_CHOICES,default="STAFF")
    is_active=models.BooleanField(default=True)
    def __str__(self): return f"{self.user.get_full_name() or self.user.username} ({self.role})"
