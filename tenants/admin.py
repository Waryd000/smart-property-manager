from django.contrib import admin
from .models import Tenant,Tenancy
admin.site.register(Tenant)
@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin): list_display=("tenant","unit","monthly_rent","start_date","due_day","status"); list_filter=("status",)
