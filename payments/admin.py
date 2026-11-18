from django.contrib import admin
from .models import Payment,PaymentAllocation,BankTransaction
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin): list_display=("bank_reference","tenant","amount","status","payment_date"); list_filter=("status","method")
admin.site.register(PaymentAllocation)
@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin): list_display=("bank_reference","transaction_date","amount","reconciliation_status","matched_payment")
