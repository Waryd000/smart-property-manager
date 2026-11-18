from django.contrib import admin
from .models import RentCharge,ManagementFee
@admin.register(RentCharge)
class RentChargeAdmin(admin.ModelAdmin): list_display=("tenancy","billing_month","amount","due_date","status"); list_filter=("status","billing_month")
admin.site.register(ManagementFee)
