from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import BankTransaction, Payment, PaymentAllocation
from rent.models import RentCharge
from tenants.models import Tenancy


@transaction.atomic
def verify_and_allocate(payment, user):
    """Verify an exact bank match and allocate only within the payment property."""
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

    has_tenancy = Tenancy.objects.filter(
        tenant=payment.tenant,
        unit__property_id=payment.property_id,
    ).exists()
    if not has_tenancy:
        raise ValueError("The payment tenant has no tenancy in this property.")

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


@transaction.atomic
def import_equity_statement_row(row):
    """Import one normalized incoming Equity Bank statement row.

    Required keys: reference, transaction_date (ISO-8601), amount.
    Optional key: narrative. Only positive incoming credits are accepted.
    Identical duplicate references are idempotent; conflicting duplicates fail.
    """
    reference = str(row.get("reference", "")).strip()
    if not reference:
        raise ValueError("A bank transaction reference is required.")

    try:
        tx_date = datetime.fromisoformat(str(row["transaction_date"]).strip().replace("Z", "+00:00"))
        amount = Decimal(str(row["amount"]).strip())
    except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
        raise ValueError(
            "Each statement row needs a valid ISO transaction date and decimal amount."
        ) from exc

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Only positive incoming transaction amounts can be imported.")

    if timezone.is_naive(tx_date):
        tx_date = timezone.make_aware(tx_date, timezone.get_current_timezone())

    existing = BankTransaction.objects.select_for_update().filter(
        bank_reference=reference
    ).first()
    if existing:
        same_date = existing.transaction_date == tx_date
        if existing.amount != amount or not same_date:
            raise ValueError(
                "This bank reference already exists with a different amount or date."
            )
        return existing, False

    try:
        with transaction.atomic():
            created = BankTransaction.objects.create(
                bank_reference=reference,
                transaction_date=tx_date,
                amount=amount,
                narrative=str(row.get("narrative", "")).strip()[:255],
            )
        return created, True
    except IntegrityError:
        # A second importer may have inserted this reference concurrently.
        existing = BankTransaction.objects.get(bank_reference=reference)
        if existing.amount != amount or existing.transaction_date != tx_date:
            raise ValueError(
                "This bank reference already exists with a different amount or date."
            )
        return existing, False
