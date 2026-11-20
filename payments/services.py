from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .models import BankTransaction, Payment, PaymentAllocation
from rent.models import RentCharge
from tenants.models import Tenancy


@transaction.atomic
def verify_and_allocate(payment, user):
    """Verify a payment after an exact bank and tenant/property match.

    Rent is allocated only to the named tenant's oldest outstanding charges
    within the selected property. Any remainder stays visibly unallocated.
    """
    payment = Payment.objects.select_for_update().get(pk=payment.pk)

    if payment.status == "VERIFIED":
        return payment
    if payment.status != "PENDING":
        raise ValueError("Only pending payments can be verified")
    if not payment.property_id:
        raise ValueError(
            "Assign this payment to a property before verification. "
            "Unassigned payments must be reviewed by a manager."
        )
    if not Tenancy.objects.filter(
        tenant_id=payment.tenant_id,
        unit__property_id=payment.property_id,
    ).exists():
        raise ValueError(
            "The selected tenant has no tenancy in this property. "
            "Correct the tenant or property before verification."
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
    payment.save(update_fields=["status", "verified_at", "verified_by", "updated_at"])

    bank_transaction.matched_payment = payment
    bank_transaction.reconciliation_status = "MATCHED"
    bank_transaction.save(
        update_fields=["matched_payment", "reconciliation_status", "updated_at"]
    )

    payment.unallocated_amount = remaining
    return payment


def import_equity_statement_row(row):
    """Import one normalized incoming-credit row idempotently.

    Expected keys: reference, transaction_date (ISO-8601), amount, narrative.
    A repeated reference is accepted only when its amount and transaction
    timestamp match the original row. Conflicts require manual reconciliation.
    """
    try:
        reference = str(row["reference"]).strip()
        transaction_date = datetime.fromisoformat(str(row["transaction_date"]))
        amount = Decimal(str(row["amount"]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(
            "Statement row requires a reference, ISO transaction_date and valid amount."
        ) from exc

    if not reference:
        raise ValueError("Bank transaction reference cannot be empty.")
    if amount <= 0:
        raise ValueError("Only positive incoming bank credits can be imported.")

    if timezone.is_naive(transaction_date):
        transaction_date = timezone.make_aware(
            transaction_date,
            timezone.get_current_timezone(),
        )

    transaction_record, created = BankTransaction.objects.get_or_create(
        bank_reference=reference,
        defaults={
            "transaction_date": transaction_date,
            "amount": amount,
            "narrative": str(row.get("narrative", ""))[:255],
        },
    )
    if not created and (
        transaction_record.amount != amount
        or transaction_record.transaction_date != transaction_date
    ):
        raise ValueError(
            "This bank reference already exists with a different amount or date. "
            "Review the statement rows manually; no existing transaction was changed."
        )

    return transaction_record, created
