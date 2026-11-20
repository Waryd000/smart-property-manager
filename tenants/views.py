import os

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from core.access import is_manager, visible_properties
from operations.models import AuditLog
from properties.models import Unit
from .models import Tenant, Tenancy
from .forms import (
    TenantForm,
    TenancyForm,
    TenancyConfirmForm,
    TenancyEndForm,
)


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
def tenant_list(request):
    allowed = visible_properties(request.user)
    visible_tenancies = (
        Tenancy.objects.filter(unit__property__in=allowed)
        .select_related("unit", "unit__property")
        .order_by("unit__property__name", "unit__unit_number")
    )
    tenants = (
        Tenant.objects.filter(
            Q(tenancies__unit__property__in=allowed)
            | Q(created_by=request.user, tenancies__isnull=True)
        )
        .distinct()
        .prefetch_related(Prefetch("tenancies", queryset=visible_tenancies))
    )
    return render(
        request,
        "tenants/list.html",
        {
            "tenants": tenants,
            "can_manage": is_manager(request.user),
        },
    )


@login_required
def tenant_create(request):
    if not visible_properties(request.user).exists():
        messages.error(request, "You need access to a property before adding tenants.")
        return redirect("dashboard")

    form = TenantForm(request.POST or None)
    if form.is_valid():
        tenant = form.save(commit=False)
        tenant.created_by = request.user
        tenant.save()
        _audit(request, "TENANT_CREATED", tenant, {"full_name": tenant.full_name})
        messages.success(request, "Tenant record created.")
        return redirect("tenant-list")
    return render(
        request,
        "properties/form.html",
        {"form": form, "title": "Add tenant"},
    )


@login_required
def tenancy_create(request):
    allowed = visible_properties(request.user)
    manager = is_manager(request.user)
    form = TenancyForm(
        request.POST or None,
        request.FILES or None,
        initial={
            "tenant": request.GET.get("tenant"),
            "status": "PENDING" if not manager else "ACTIVE",
        },
    )
    form.fields["unit"].queryset = Unit.objects.filter(property__in=allowed)
    form.fields["tenant"].queryset = Tenant.objects.filter(
        Q(tenancies__unit__property__in=allowed)
        | Q(created_by=request.user, tenancies__isnull=True)
    ).distinct()

    # Staff may create a proposed tenancy only. Activation is a manager
    # confirmation action which records the real move-in date.
    if not manager:
        form.fields["status"].choices = [("PENDING", "Pending verification")]
        form.fields["status"].initial = "PENDING"

    if form.is_valid():
        try:
            with transaction.atomic():
                tenancy = form.save()
                if tenancy.status == "ACTIVE":
                    Unit.objects.filter(pk=tenancy.unit_id).update(status="OCCUPIED")
                _audit(
                    request,
                    "TENANCY_CREATED",
                    tenancy,
                    {
                        "tenant_id": tenancy.tenant_id,
                        "unit_id": tenancy.unit_id,
                        "status": tenancy.status,
                    },
                )
        except IntegrityError:
            form.add_error(
                "unit",
                "This unit already has an active tenancy. "
                "Refresh and review its current occupancy.",
            )
        else:
            messages.success(
                request,
                "Tenancy record created. Pending records must be confirmed by a manager.",
            )
            return redirect("tenant-list")

    return render(
        request,
        "properties/form.html",
        {"form": form, "title": "Create tenancy"},
    )


@login_required
@transaction.atomic
def tenancy_confirm(request, pk):
    if request.method != "POST":
        return redirect("tenant-list")
    if not is_manager(request.user):
        messages.error(request, "Only a manager can confirm occupancy.")
        return redirect("tenant-list")

    tenancy = get_object_or_404(
        Tenancy.objects.select_for_update().select_related("unit", "tenant"),
        pk=pk,
        unit__property__in=visible_properties(request.user),
    )
    if tenancy.status != "PENDING":
        messages.error(request, "Only pending tenancies can be confirmed.")
        return redirect("tenant-list")

    form = TenancyConfirmForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid confirmed tenancy start date.")
        return redirect("tenant-list")

    start_date = form.cleaned_data["start_date"]
    if tenancy.end_date and tenancy.end_date < start_date:
        messages.error(request, "The tenancy end date cannot be before its start date.")
        return redirect("tenant-list")
    if Tenancy.objects.filter(unit=tenancy.unit, status="ACTIVE").exclude(pk=tenancy.pk).exists():
        messages.error(request, "This unit already has an active tenancy.")
        return redirect("tenant-list")

    previous = tenancy.status
    tenancy.status = "ACTIVE"
    tenancy.start_date = start_date
    try:
        with transaction.atomic():
            tenancy.full_clean()
            tenancy.save(update_fields=["status", "start_date", "updated_at"])
    except (IntegrityError, ValidationError) as exc:
        messages.error(request, f"Could not confirm this tenancy: {exc}")
        return redirect("tenant-list")

    Unit.objects.filter(pk=tenancy.unit_id).update(status="OCCUPIED")
    _audit(
        request,
        "TENANCY_CONFIRMED",
        tenancy,
        {"from": previous, "to": "ACTIVE", "start_date": start_date.isoformat()},
    )
    messages.success(request, "Tenancy confirmed and unit marked occupied.")
    return redirect("tenant-list")


@login_required
@transaction.atomic
def tenancy_end(request, pk):
    if request.method != "POST":
        return redirect("tenant-list")
    if not is_manager(request.user):
        messages.error(request, "Only a manager can end a tenancy.")
        return redirect("tenant-list")

    tenancy = get_object_or_404(
        Tenancy.objects.select_for_update().select_related("unit"),
        pk=pk,
        unit__property__in=visible_properties(request.user),
        status="ACTIVE",
    )
    form = TenancyEndForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid final occupancy date.")
        return redirect("tenant-list")

    end_date = form.cleaned_data["end_date"]
    if tenancy.start_date and end_date < tenancy.start_date:
        messages.error(request, "The end date cannot be before the tenancy start date.")
        return redirect("tenant-list")

    tenancy.status = "ENDED"
    tenancy.end_date = end_date
    tenancy.save(update_fields=["status", "end_date", "updated_at"])
    if not Tenancy.objects.filter(unit=tenancy.unit, status="ACTIVE").exists():
        Unit.objects.filter(pk=tenancy.unit_id, status="OCCUPIED").update(status="VACANT")

    _audit(
        request,
        "TENANCY_ENDED",
        tenancy,
        {"end_date": end_date.isoformat()},
    )
    messages.success(request, "Tenancy ended and occupancy status updated.")
    return redirect("tenant-list")


@login_required
def tenancy_agreement_download(request, pk):
    tenancy = get_object_or_404(
        Tenancy.objects.select_related("unit__property"),
        pk=pk,
        unit__property__in=visible_properties(request.user),
    )
    if not tenancy.agreement_file:
        raise Http404("No agreement is attached to this tenancy.")

    try:
        file_handle = tenancy.agreement_file.storage.open(tenancy.agreement_file.name, "rb")
    except (FileNotFoundError, OSError):
        raise Http404("The agreement file is not available.")

    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=os.path.basename(tenancy.agreement_file.name),
        content_type="application/octet-stream",
    )
