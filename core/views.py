from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.shortcuts import render
from properties.models import Property, Unit
from tenants.models import Tenant, Tenancy
from rent.models import RentCharge
from payments.models import Payment
from django.utils import timezone
from decimal import Decimal
@login_required
def dashboard(request):
    today=timezone.localdate()
    charges=RentCharge.objects.all()
    outstanding=sum((c.balance for c in charges if c.balance > 0), Decimal("0.00"))
    context={"property_count":Property.objects.count(),"unit_count":Unit.objects.count(),"occupied_count":Unit.objects.filter(status="OCCUPIED").count(),"tenant_count":Tenant.objects.count(),"outstanding":outstanding,"overdue_count":charges.filter(due_date__lt=today).exclude(status="PAID").count(),"recent_payments":Payment.objects.filter(status="VERIFIED").order_by("-verified_at")[:8]}
    return render(request,"core/dashboard.html",context)
