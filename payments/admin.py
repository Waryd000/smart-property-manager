from django.contrib import admin

from .models import BankTransaction, Payment, PaymentAllocation


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("bank_reference", "tenant", "property", "amount", "status", "payment_date")
    list_filter = ("status", "method", "property")
    search_fields = ("bank_reference", "tenant__full_name")


admin.site.register(PaymentAllocation)


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
