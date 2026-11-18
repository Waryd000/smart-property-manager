from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from core.access import is_manager,visible_properties
from .models import Payment
from .services import verify_and_allocate
@login_required
def payment_list(request):
    payments=Payment.objects.select_related("tenant").filter(tenant__tenancies__unit__property__in=visible_properties(request.user)).distinct().order_by("-created_at")
    return render(request,"rent/payments.html",{"payments":payments})
@login_required
def verify_payment(request,pk):
    if request.method!="POST": return redirect("payment-list")
    payment=get_object_or_404(Payment,pk=pk,tenant__tenancies__unit__property__in=visible_properties(request.user))
    if not is_manager(request.user):
        messages.error(request,"Only a manager can verify payments."); return redirect("payment-list")
    try: verify_and_allocate(payment,request.user); messages.success(request,"Payment verified and allocated.")
    except ValueError as exc: messages.error(request,str(exc))
    return redirect("payment-list")
