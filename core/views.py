from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from payments.models import Payment
from properties.models import Property, Unit
from rent.models import RentCharge
from tenants.models import Tenant


@login_required
def dashboard(request):
    today = timezone.localdate()
    charges = RentCharge.objects.all()
    outstanding = sum(
        (charge.balance for charge in charges if charge.balance > 0),
        Decimal("0.00"),
    )

    # Review flags are generated from the source notes stored on imported units.
    # No uncertain source record is silently treated as a verified tenancy.
    spreadsheet_review_flags = []
    review_units = (
        Unit.objects.filter(notes__contains="REVIEW:")
        .select_related("property")
        .prefetch_related("tenancies__tenant")
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

    context = {
        "property_count": Property.objects.count(),
        "unit_count": Unit.objects.count(),
        "occupied_count": Unit.objects.filter(status="OCCUPIED").count(),
        "tenant_count": Tenant.objects.count(),
        "outstanding": outstanding,
        "overdue_count": charges.filter(due_date__lt=today).exclude(status="PAID").count(),
        "recent_payments": Payment.objects.filter(status="VERIFIED").order_by("-verified_at")[:8],
        "spreadsheet_review_flags": spreadsheet_review_flags,
    }
    return render(request, "core/dashboard.html", context)
