from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models import Prefetch
from django.shortcuts import render
from django.utils import timezone

from core.access import visible_properties
from payments.models import Payment
from properties.models import Property, Unit
from rent.models import RentCharge
from tenants.models import Tenant, Tenancy


@login_required
def dashboard(request):
    today = timezone.localdate()
    properties = visible_properties(request.user)
    units = Unit.objects.filter(property__in=properties)
    tenants = Tenant.objects.filter(
        tenancies__unit__property__in=properties
    ).distinct()

    # Scope every financial total and activity list to the user's visible
    # portfolio. Annotating allocations avoids one balance query per charge.
    charges = (
        RentCharge.objects.filter(tenancy__unit__property__in=properties)
        .annotate(
            allocated_total=Coalesce(
                Sum("allocations__allocated_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .annotate(balance_amount=F("amount") - F("allocated_total"))
    )
    outstanding = (
        charges.filter(balance_amount__gt=0)
        .aggregate(total=Sum("balance_amount"))["total"]
        or Decimal("0.00")
    )

    # Review flags are generated from source notes on visible imported units.
    # The latest tenancy is used so an old ended tenancy cannot mask a newer
    # tenant record. Uncertain source records are never treated as verified.
    spreadsheet_review_flags = []
    review_units = (
        units.filter(notes__contains="REVIEW:")
        .select_related("property")
        .prefetch_related(
            Prefetch(
                "tenancies",
                queryset=Tenancy.objects.select_related("tenant").order_by("-created_at"),
            )
        )
        .order_by("property__name", "unit_number")
    )
    for unit in review_units:
        tenancy = next(iter(unit.tenancies.all()), None)
        source_notes, issue = unit.notes.split("REVIEW:", 1)
        spreadsheet_review_flags.append({
            "property": unit.property.name,
            "unit_number": unit.unit_number,
            "listed_name": tenancy.tenant.full_name if tenancy else "No tenant name recorded",
            "source": source_notes.strip(),
            "issue": issue.strip(),
        })

    recent_payments = (
        Payment.objects.filter(
            status="VERIFIED",
            tenant__tenancies__unit__property__in=properties,
        )
        .select_related("tenant")
        .distinct()
        .order_by("-verified_at")[:8]
    )

    context = {
        "property_count": properties.count(),
        "unit_count": units.count(),
        "occupied_count": units.filter(status="OCCUPIED").count(),
        "tenant_count": tenants.count(),
        "outstanding": outstanding,
        "overdue_count": charges.filter(
            due_date__lt=today,
            balance_amount__gt=0,
        ).count(),
        "recent_payments": recent_payments,
        "spreadsheet_review_flags": spreadsheet_review_flags,
    }
    return render(request, "core/dashboard.html", context)
