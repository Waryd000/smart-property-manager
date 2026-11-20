from django.contrib import admin

from .models import BankTransaction, Payment, PaymentAllocation


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "bank_reference",
        "tenant",
        "property",
        "amount",
        "unallocated_amount",
        "status",
        "payment_date",
    )
    list_filter = ("status", "method", "property")
    search_fields = ("bank_reference", "tenant__full_name")
    readonly_fields = ("status", "verified_at", "verified_by", "unallocated_amount")


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ("payment", "rent_charge", "allocated_amount", "created_at")
    readonly_fields = ("payment", "rent_charge", "allocated_amount", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "bank_reference",
        "transaction_date",
        "amount",
        "reconciliation_status",
        "matched_payment",
    )
    list_filter = ("reconciliation_status", "bank_name")
    search_fields = ("bank_reference", "narrative")
    readonly_fields = ("reconciliation_status", "matched_payment")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.matched_payment_id:
            fields.extend(
                field.name
                for field in self.model._meta.fields
                if field.name not in fields
            )
        return tuple(fields)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.matched_payment_id:
            return False
        return super().has_delete_permission(request, obj)
