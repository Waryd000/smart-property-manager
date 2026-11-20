import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from core.access import is_manager, visible_properties
from .forms import BankStatementImportForm, PaymentRecordForm
from .models import Payment
from operations.models import AuditLog
from .services import (
    import_equity_statement_row,
    reverse_verified_payment,
    verify_and_allocate,
)



@login_required
def payment_list(request):
    payments = Payment.objects.select_related("tenant", "property")
    if not is_manager(request.user):
        payments = payments.filter(property__in=visible_properties(request.user))
    payments = payments.order_by("-created_at")
    return render(
        request,
        "rent/payments.html",
        {"payments": payments, "can_manage": is_manager(request.user)},
    )


@login_required
def bank_statement_import(request):
    if not is_manager(request.user):
        messages.error(request, "Only an active manager can import bank statements.")
        return redirect("payment-list")

    form = BankStatementImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        uploaded = form.cleaned_data["statement_file"]
        try:
            raw = uploaded.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValueError("The CSV must use UTF-8 text encoding.") from exc

            reader = csv.DictReader(io.StringIO(text), strict=True)
            if not reader.fieldnames:
                raise ValueError("The CSV file is empty or has no header row.")

            header_names = [
                str(name).strip().lower()
                for name in reader.fieldnames
                if name is not None
            ]
            if len(header_names) != len(set(header_names)):
                raise ValueError("The CSV contains duplicate column headings.")
            normalized_headers = set(header_names)
            required_headers = {"reference", "transaction_date", "amount"}
            missing = sorted(required_headers - normalized_headers)
            if missing:
                raise ValueError(
                    "Missing required CSV columns: " + ", ".join(missing)
                )

            created_count = 0
            duplicate_count = 0
            row_count = 0
            with transaction.atomic():
                for line_number, source_row in enumerate(reader, start=2):
                    if None in source_row:
                        raise ValueError(f"CSV row {line_number}: unexpected extra column values.")
                    row = {
                        str(key).strip().lower(): (value or "").strip()
                        for key, value in source_row.items()
                        if key is not None
                    }
                    if not any(row.values()):
                        continue
                    row_count += 1
                    if row_count > 5000:
                        raise ValueError("A single CSV import cannot exceed 5,000 transaction rows.")
                    try:
                        _, created = import_equity_statement_row(row)
                    except ValueError as exc:
                        raise ValueError(f"CSV row {line_number}: {exc}") from exc
                    if created:
                        created_count += 1
                    else:
                        duplicate_count += 1

                if row_count == 0:
                    raise ValueError("The CSV contains no transaction rows.")
                AuditLog.objects.create(
                    user=request.user,
                    action="BANK_STATEMENT_IMPORTED",
                    model_name="BankTransaction",
                    details={
                        "file_name": uploaded.name[:255],
                        "new_transactions": created_count,
                        "identical_duplicates_skipped": duplicate_count,
                        "rows_processed": row_count,
                    },
                    ip_address=request.META.get("REMOTE_ADDR") or None,
                )

            messages.success(
                request,
                f"Bank statement processed: {created_count} new transactions imported; "
                f"{duplicate_count} identical existing transactions skipped.",
            )
            return redirect("payment-list")
        except (ValueError, csv.Error) as exc:
            messages.error(request, str(exc) or "The CSV file could not be parsed.")

    return render(request, "payments/bank_import.html", {"form": form})


@login_required
def payment_create(request):
    if not is_manager(request.user):
        messages.error(request, "Only an active manager can record pending payments.")
        return redirect("payment-list")

    form = PaymentRecordForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            payment = form.save(commit=False)
            payment.status = "PENDING"
            payment.method = "BANK_TRANSFER"
            payment.save()
            AuditLog.objects.create(
                user=request.user,
                action="PAYMENT_RECORDED_PENDING",
                model_name="Payment",
                record_id=str(payment.pk),
                details={
                    "bank_reference": payment.bank_reference,
                    "amount": str(payment.amount),
                    "property_id": payment.property_id,
                    "tenant_id": payment.tenant_id,
                },
                ip_address=request.META.get("REMOTE_ADDR") or None,
            )
        messages.success(
            request,
            "Pending payment recorded. It must match an imported bank transaction before verification.",
        )
        return redirect("payment-list")

    return render(
        request,
        "payments/payment_form.html",
        {"form": form},
    )


@login_required
def verify_payment(request, pk):
    if request.method != "POST":
        return redirect("payment-list")

    if not is_manager(request.user):
        messages.error(request, "Only an active manager can verify payments.")
        return redirect("payment-list")

    payment = get_object_or_404(
        Payment.objects.select_related("tenant", "property"),
        pk=pk,
    )
    if not payment.property_id:
        messages.error(
            request,
            "Assign this payment to a property before verification.",
        )
        return redirect("payment-list")

    if not visible_properties(request.user).filter(pk=payment.property_id).exists():
        messages.error(request, "You do not have access to this property's payments.")
        return redirect("payment-list")

    try:
        verified = verify_and_allocate(payment, request.user)
        unallocated = verified.unallocated_amount
        if unallocated > 0:
            messages.warning(
                request,
                "Payment matched and verified. "
                f"UGX {unallocated:,.0f} remains unallocated; "
                "record a controlled tenant credit or refund before using it."
            )
        else:
            messages.success(request, "Payment matched, verified and allocated.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("payment-list")


@login_required
def reverse_payment_view(request, pk):
    if request.method != "POST":
        return redirect("payment-list")
    if not is_manager(request.user):
        messages.error(request, "Only an active manager can reverse payments.")
        return redirect("payment-list")

    payment = get_object_or_404(
        Payment.objects.select_related("property"),
        pk=pk,
        property__in=visible_properties(request.user),
    )
    reason = request.POST.get("reason", "").strip()
    try:
        reverse_verified_payment(payment, request.user, reason)
        messages.success(
            request,
            "Payment reversed. Its allocations were removed from rent balances and the original bank match was retained for audit.",
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("payment-list")
