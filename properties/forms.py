from django import forms
from .models import Property,Unit
class PropertyForm(forms.ModelForm):
 class Meta: model=Property; fields=["name","address","description","status","landlord"]
class UnitForm(forms.ModelForm):
 class Meta: model=Unit; fields=["property","unit_number","monthly_rent","status","notes"]
