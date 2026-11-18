from django import forms
from .models import Tenant,Tenancy
class TenantForm(forms.ModelForm):
 class Meta: model=Tenant; fields=["full_name","phone","email","identification_reference","emergency_contact","notes"]
class TenancyForm(forms.ModelForm):
 class Meta: model=Tenancy; fields=["tenant","unit","start_date","end_date","monthly_rent","deposit_amount","due_day","status","agreement_file"]
