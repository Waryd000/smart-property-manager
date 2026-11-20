import calendar
from datetime import date, datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from tenants.models import Tenancy
from .models import RentCharge


def safe_due_date(year, month, day):
    """Return a valid date, clamping a requested day to the month's end."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(int(day), 1), last_day))


@transaction.atomic
def generate_monthly_charges(billing_month=None):
    """Create one monthly charge for every tenancy active during the month.

    billing_month accepts a date/datetime or an ISO date string. The day is
    normalized to the first of the month so callers cannot accidentally create
    multiple charges for different days within the same calendar month.
    Existing tenancy/month charges are never overwritten.
    """
    if billing_month is None:
        billing_month = timezone.localdate()
    elif isinstance(billing_month, str):
        try:
            billing_month = date.fromisoformat(billing_month)
        except ValueError as exc:
            raise ValueError("billing_month must be a valid ISO date.") from exc
    elif not isinstance(billing_month, (date, datetime)):
        raise ValueError("billing_month must be a date or ISO date string.")

    billing_month = date(billing_month.year, billing_month.month, 1)
    next_month = date(
        billing_month.year + (billing_month.month == 12),
        (billing_month.month % 12) + 1,
        1,
    )

    created = []
    active_tenancies = (
        Tenancy.objects.select_related("unit", "tenant")
        .filter(status="ACTIVE", start_date__lt=next_month)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=billing_month))
        .order_by("id")
    )

    for tenancy in active_tenancies:
        due_date = safe_due_date(
            billing_month.year,
            billing_month.month,
            tenancy.due_day,
        )
        charge, was_created = RentCharge.objects.get_or_create(
            tenancy=tenancy,
            billing_month=billing_month,
            defaults={
                "amount": tenancy.monthly_rent,
                "due_date": due_date,
            },
        )
        if was_created:
            created.append(charge)

    return created
