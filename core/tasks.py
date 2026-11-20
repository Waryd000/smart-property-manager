from celery import shared_task
from django.utils import timezone

from rent.services import generate_monthly_charges


@shared_task(name="core.tasks.generate_monthly_rent_charges")
def generate_monthly_rent_charges():
    """Generate this Kampala-local calendar month's rent charges idempotently."""
    billing_month = timezone.localdate().replace(day=1)
    created = generate_monthly_charges(billing_month)
    return {
        "billing_month": billing_month.isoformat(),
        "created_count": len(created),
    }
