from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from core.access import visible_properties
from .models import RentCharge


@login_required
def rent_list(request):
    allocated_total = Coalesce(
        Sum("allocations__allocated_amount"),
        Value(Decimal("0.00")),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    charges = (
        RentCharge.objects.select_related(
            "tenancy__tenant",
            "tenancy__unit__property",
        )
        .filter(tenancy__unit__property__in=visible_properties(request.user))
        .annotate(amount_paid_total=allocated_total)
        .annotate(balance_amount=F("amount") - F("amount_paid_total"))
        .order_by("due_date", "id")
    )
    return render(
        request,
        "rent/list.html",
        {
            "charges": charges,
            "today": timezone.localdate(),
        },
    )
