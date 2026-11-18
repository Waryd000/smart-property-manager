from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from payments.models import Payment
from properties.models import Property, Unit
from rent.models import RentCharge


@login_required
def dashboard(request):
    today = timezone.localdate()
    charges = RentCharge.objects.all()
    outstanding = sum(
        (charge.balance for charge in charges if charge.balance > 0),
        Decimal("0.00"),
    )

    # These records came from the latest tenant register in the supplied
    # workbook. They are shown as review items, not treated as verified
    # active tenancies until the user confirms their current occupancy.
    spreadsheet_review_flags = [
        {
            "property": "Sir Apollo",
            "unit_number": "23",
            "listed_name": "MUHAMMAD",
            "source": "NAHA ASSETS 11234.xlsx — SIR APOLLO, row 469",
            "issue": "Confirm that the unit and tenancy are still current.",
        },
        {
            "property": "Sir Apollo",
            "unit_number": "24",
            "listed_name": "joush",
            "source": "NAHA ASSETS 11234.xlsx — SIR APOLLO, row 470",
            "issue": "Confirm that the unit and tenancy are still current.",
        },
    ]

    context = {
        "property_count": Property.objects.count(),
        "unit_count": Unit.objects.count(),
        "occupied_count": Unit.objects.filter(status="OCCUPIED").count(),
        "tenant_count": Property.objects.count() and sum(
            prop.tenants.count() for prop in Property.objects.none()
        ) or 0,
        "outstanding": outstanding,
        "overdue_count": charges.filter(due_date__lt=today).exclude(status="PAID").count(),
        "recent_payments": Payment.objects.filter(status="VERIFIED").order_by("-verified_at")[:8],
        "spreadsheet_review_flags": spreadsheet_review_flags,
    }
    return render(request, "core/dashboard.html", context)
