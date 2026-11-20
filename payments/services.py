from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import BankTransaction, Payment, PaymentAllocation
from rent.models import RentCharge


@transaction.atomic
def verify_and_allocate(payment, user):
    """Verify a payment only after an exact bank and property match.

    Rent is allocated only to the named tenant's oldest outstanding charges
    within the property's scope. Any remainder is persisted as unallocated.
    """
    payment = Payment.objects.select_for_update().select_related("property").get(pk=payment.pk)

    if payment.status == "VERIFIED":
        return payment
    if payment.status != "PENDING":
        raise ValueError("Only pending payments can be verified")
    if not payment.property_id:
        raise ValueError(
            "Assign this payment to a property before verification. "
            "Unassigned payments must be reviewed by a manager."
        )

    bank_transaction = (
        BankTransaction.objects.select_for_update()
        .filter(bank_reference=payment.bank_reference)
        .first()
    )
    if bank_transaction is None:
        raise ValueError(
            "No imported bank transaction matches this payment reference. "
            "Import or record the bank transaction before verifying."
        )
    if bank_transaction.amount != payment.amount:
        raise ValueError(
            "The payment amount does not match the imported bank transaction."
        )
    if (
        bank_transaction.matched_payment_id is not None
        and bank_transaction.matched_payment_id != payment.pk
    ):
        raise ValueError("This bank transaction is already matched to another payment.")

    remaining = payment.amount
    charges = (
        RentCharge.objects.select_for_update()
        .filter(
            tenancy__tenant=payment.tenant,
            tenancy__unit__property_id=payment.property_id,
        )
        .exclude(status="PAID")
        .order_by("due_date", "id")
    )
    for charge in charges:
        outstanding = max(Decimal("0.00"), charge.amount - charge.amount_paid)
        if outstanding <= 0:
            continue
        portion = min(remaining, outstanding)
        if portion:
            PaymentAllocation.objects.create(
                payment=payment,
                rent_charge=charge,
                allocated_amount=portion,
            )
            remaining -= portion
            charge.refresh_status()
        if remaining <= 0:
            break

    payment.status = "VERIFIED"
    payment.verified_at = timezone.now()
    payment.verified_by = user
    payment.unallocated_amount = remaining
    payment.save(
        update_fields=[
            "status",
            "verified_at",
            "verified_by",
            "unallocated_amount",
            "updated_at",
        ]
    )

    bank_transaction.matched_payment = payment
    bank_transaction.reconciliation_status = "MATCHED"
    bank_transaction.save(
        update_fields=["matched_payment", "reconciliation_status", "updated_at"]
    )
    return payment


def import_equity_statement_row(row):
    """Create an unmatched bank transaction from a normalized CSV row.

    Expected keys: reference, transaction_date (ISO format), amount, narrative.
    Map the Equity Bank's actual CSV headers before using this function.
    """
    from datetime import datetime

    tx_date = datetime.fromisoformat(row["transaction_date"])
    return BankTransaction.objects.get_or_create(
        bank_reference=row["reference"],
        defaults={
            "transaction_date": tx_date,
            "amount": Decimal(row["amount"]),
            "narrative": row.get("narrative", ""),
        },
    )
