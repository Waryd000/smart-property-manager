import calendar
from datetime import date
from django.db import transaction
from django.utils import timezone
from tenants.models import Tenancy
from .models import RentCharge

def safe_due_date(year, month, day):
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))

@transaction.atomic
def generate_monthly_charges(billing_month=None):
    billing_month=billing_month or timezone.localdate().replace(day=1)
    from datetime import date
    from django.db.models import Q
    next_month = date(billing_month.year + (billing_month.month == 12), (billing_month.month % 12) + 1, 1)
    created=[]
    active_tenancies = Tenancy.objects.select_related("unit","tenant").filter(
        status="ACTIVE", start_date__lt=next_month
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=billing_month))
    for tenancy in active_tenancies:
        due=safe_due_date(billing_month.year,billing_month.month,tenancy.due_day)
        charge,was_created=RentCharge.objects.get_or_create(tenancy=tenancy,billing_month=billing_month,defaults={"amount":tenancy.monthly_rent,"due_date":due})
        if was_created: created.append(charge)
    return created

