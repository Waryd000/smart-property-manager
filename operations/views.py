from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.access import is_manager, visible_properties
from .forms import ExpenseForm, MaintenanceRequestForm
from .models import AuditLog, Expense, MaintenanceRequest


MAINTENANCE_TRANSITIONS = {
    "OPEN": {"REVIEW", "CANCELLED"},
    "REVIEW": {"APPROVED", "CANCELLED"},
    "APPROVED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}
EXPENSE_TRANSITIONS = {
    "PENDING": {"APPROVED", "REJECTED"},
    "APPROVED": {"PAID"},
    "PAID": set(),
    "REJECTED": set(),
}


def _audit(request, action, instance, details):
    AuditLog.objects.create(
        user=request.user,
        action=action,
        model_name=instance.__class__.__name__,
        record_id=str(instance.pk),
        details=details,
        ip_address=request.META.get("REMOTE_ADDR") or None,
    )


@login_required
def maintenance_list(request):
    items = (
        MaintenanceRequest.objects.filter(property__in=visible_properties(request.user))
        .select_related("property", "unit", "assigned_to")
        .order_by("-created_at")
    )
    return render(
        request, "operations/maintenance_list.html",
        {"maintenance_requests": items, "can_manage": is_manager(request.user)},
    )


@login_required
def maintenance_create(request):
    form = MaintenanceRequestForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.reported_by = request.user.get_full_name() or request.user.username
        item.status = "OPEN"
        item.save()
        _audit(request, "MAINTENANCE_REQUEST_CREATED", item, {
            "property_id": item.property_id,
            "unit_id": item.unit_id,
            "priority": item.priority,
        })
        messages.success(request, "Maintenance request submitted.")
        return redirect("maintenance-list")
    return render(request, "operations/maintenance_form.html", {
        "form": form, "title": "Report maintenance",
    })


@login_required
@transaction.atomic
def maintenance_transition(request, pk):
    if request.method != "POST":
        return redirect("maintenance-list")
    if not is_manager(request.user):
        messages.error(request, "Only a manager can update maintenance status.")
        return redirect("maintenance-list")

    item = get_object_or_404(
        MaintenanceRequest.objects.select_for_update(),
        pk=pk,
        property__in=visible_properties(request.user),
    )
    new_status = request.POST.get("status", "").strip().upper()
    if new_status not in MAINTENANCE_TRANSITIONS.get(item.status, set()):
        messages.error(request, "That maintenance status transition is not allowed.")
        return redirect("maintenance-list")

    if new_status == "COMPLETED":
        raw_cost = request.POST.get("actual_cost", "").strip()
        if raw_cost:
            try:
                actual_cost = Decimal(raw_cost)
                if not actual_cost.is_finite() or actual_cost < 0:
                    raise InvalidOperation
                item.actual_cost = actual_cost
            except (InvalidOperation, ValueError):
                messages.error(request, "Enter a valid non-negative actual cost.")
                return redirect("maintenance-list")

    previous = item.status
    item.status = new_status
    if new_status == "COMPLETED":
        item.completed_at = timezone.now()
    item.save(update_fields=["status", "actual_cost", "completed_at", "updated_at"])
    _audit(request, "MAINTENANCE_STATUS_CHANGED", item, {
        "from": previous,
        "to": new_status,
        "actual_cost": str(item.actual_cost) if item.actual_cost is not None else None,
    })
    messages.success(request, f"Maintenance request moved to {item.get_status_display()}.")
    return redirect("maintenance-list")


@login_required
def expense_list(request):
    items = (
        Expense.objects.filter(property__in=visible_properties(request.user))
        .select_related("property", "approved_by", "paid_by")
        .order_by("-incurred_on", "-created_at")
    )
    return render(
        request, "operations/expense_list.html",
        {"expenses": items, "can_manage": is_manager(request.user)},
    )


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.status = "PENDING"
        item.save()
        _audit(request, "EXPENSE_SUBMITTED", item, {
            "property_id": item.property_id,
            "amount": str(item.amount),
            "category": item.category,
        })
        messages.success(request, "Expense submitted for manager approval.")
        return redirect("expense-list")
    return render(request, "operations/expense_form.html", {
        "form": form, "title": "Submit expense",
    })


@login_required
@transaction.atomic
def expense_transition(request, pk):
    if request.method != "POST":
        return redirect("expense-list")
    if not is_manager(request.user):
        messages.error(request, "Only a manager can approve or pay expenses.")
        return redirect("expense-list")

    item = get_object_or_404(
        Expense.objects.select_for_update(),
        pk=pk,
        property__in=visible_properties(request.user),
    )
    new_status = request.POST.get("status", "").strip().upper()
    if new_status not in EXPENSE_TRANSITIONS.get(item.status, set()):
        messages.error(request, "That expense status transition is not allowed.")
        return redirect("expense-list")

    previous = item.status
    if new_status == "PAID":
        reference = request.POST.get("payment_reference", "").strip()
        if not reference:
            messages.error(request, "Enter the payment or voucher reference before marking this expense paid.")
            return redirect("expense-list")
        item.payment_reference = reference[:120]
        item.paid_at = timezone.now()
        item.paid_by = request.user
    elif new_status == "APPROVED":
        item.approved_by = request.user

    item.status = new_status
    item.save(update_fields=[
        "status", "approved_by", "paid_by", "paid_at",
        "payment_reference", "updated_at",
    ])
    _audit(request, "EXPENSE_STATUS_CHANGED", item, {
        "from": previous,
        "to": new_status,
        "payment_reference": item.payment_reference if new_status == "PAID" else None,
    })
    messages.success(request, f"Expense moved to {item.get_status_display()}.")
    return redirect("expense-list")
