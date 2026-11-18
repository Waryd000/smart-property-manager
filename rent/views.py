from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from core.access import visible_properties
from .models import RentCharge
@login_required
def rent_list(request):
    charges=RentCharge.objects.select_related("tenancy__tenant","tenancy__unit__property").filter(tenancy__unit__property__in=visible_properties(request.user))
    return render(request,"rent/list.html",{"charges":charges})
