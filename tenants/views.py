from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.shortcuts import render, redirect

from core.access import visible_properties
from properties.models import Unit
from .models import Tenant, Tenancy
from .forms import TenantForm, TenancyForm


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
    return render(request, "tenants/list.html", {"tenants": tenants})


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
        messages.success(request, "Tenant record created.")
        return redirect("tenant-list")
    return render(request, "properties/form.html", {"form": form, "title": "Add tenant"})


@login_required
def tenancy_create(request):
    allowed = visible_properties(request.user)
    form = TenancyForm(
        request.POST or None,
        request.FILES or None,
        initial={"tenant": request.GET.get("tenant")} if request.GET.get("tenant") else None,
    )
    form.fields["unit"].queryset = Unit.objects.filter(property__in=allowed)
    form.fields["tenant"].queryset = Tenant.objects.filter(
        Q(tenancies__unit__property__in=allowed)
        | Q(created_by=request.user, tenancies__isnull=True)
    ).distinct()

    if form.is_valid():
        try:
            # The database constraint is the final guard if two requests race
            # to activate the same unit after both forms have validated.
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(
                "unit",
                "This unit already has an active tenancy. "
                "Refresh the page and review the current occupancy.",
            )
        else:
            messages.success(request, "Tenancy record created.")
            return redirect("tenant-list")

    return render(
        request,
        "properties/form.html",
        {"form": form, "title": "Create tenancy"},
    )
