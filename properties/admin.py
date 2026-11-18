from django.contrib import admin
from .models import Landlord,Property,Unit,PropertyAssignment
admin.site.register(Landlord)
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin): list_display=("name","landlord","address","status"); list_filter=("status",)
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin): list_display=("unit_number","property","monthly_rent","status"); list_filter=("status","property")
admin.site.register(PropertyAssignment)
