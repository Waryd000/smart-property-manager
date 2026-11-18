from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Payment,PaymentAllocation,BankTransaction
from rent.models import RentCharge

@transaction.atomic
def verify_and_allocate(payment, user):
    payment=Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == "VERIFIED": return payment
    if payment.status != "PENDING": raise ValueError("Only pending payments can be verified")
    remaining=payment.amount
    # Allocate oldest outstanding rent for this tenant first.
    charges=RentCharge.objects.select_for_update().filter(tenancy__tenant=payment.tenant).exclude(status="PAID").order_by("due_date","id")
    for charge in charges:
        outstanding=max(Decimal("0.00"),charge.amount-charge.amount_paid)
        if outstanding <= 0: continue
        portion=min(remaining,outstanding)
        if portion:
            PaymentAllocation.objects.create(payment=payment,rent_charge=charge,allocated_amount=portion)
            remaining-=portion
            charge.refresh_status()
        if remaining <= 0: break
    payment.status="VERIFIED"
    payment.verified_at=timezone.now()
    payment.verified_by=user
    payment.save(update_fields=["status","verified_at","verified_by","updated_at"])
    return payment

def import_equity_statement_row(row):
    """Create an unmatched bank transaction from a normalized CSV row.
    Expected keys: reference, transaction_date (ISO), amount, narrative.
    Map the Equity Bank's actual CSV headers before using this function.
    """
    from datetime import datetime
    tx_date=datetime.fromisoformat(row["transaction_date"])
    return BankTransaction.objects.get_or_create(bank_reference=row["reference"],defaults={"transaction_date":tx_date,"amount":Decimal(row["amount"]),"narrative":row.get("narrative","")})
