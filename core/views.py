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

    # Review-only entries copied from the latest SIR APOLLO register in
    # NAHA ASSETS 11234.xlsx. Do not treat these as confirmed tenancies.
    spreadsheet_review_flags = [
        {
            "property": "Sir Apollo",
            "unit_number": "23",
            "listed_name": "MUHAMMAD",
            "source": "NAHA ASSETS 11234.xlsx — SIR APOLLO, row 469",
            "issue": "Please confirm whether this unit is currently occupied and whether this tenant record is still current.",
        },
        {
            "property": "Sir Apollo",
            "unit_number": "24",
            "listed_name": "joush",
            "source": "NAHA ASSETS 11234.xlsx — SIR APOLLO, row 470",
            "issue": "Please confirm whether this unit is currently occupied and whether this tenant record is still current.",
        },
    ]

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
