from django.contrib import admin
from .models import UtilityBill,MaintenanceRequest,Expense,AuditLog
admin.site.register(UtilityBill)
admin.site.register(MaintenanceRequest)
admin.site.register(Expense)
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin): list_display=("created_at","user","action","model_name","record_id"); readonly_fields=("created_at","updated_at","user","action","model_name","record_id","details","ip_address")
