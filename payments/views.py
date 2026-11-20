from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.access import is_manager, visible_properties
from .models import Payment
from .services import verify_and_allocate


@login_required
def payment_list(request):
    payments = Payment.objects.select_related("tenant", "property")
    if not is_manager(request.user):
        payments = payments.filter(property__in=visible_properties(request.user))
    payments = payments.order_by("-created_at")
    return render(request, "rent/payments.html", {"payments": payments})


@login_required
def verify_payment(request, pk):
    if request.method != "POST":
        return redirect("payment-list")

    if not is_manager(request.user):
        messages.error(request, "Only an active manager can verify payments.")
        return redirect("payment-list")

    payment = get_object_or_404(
        Payment.objects.select_related("tenant", "property"),
        pk=pk,
    )
    if not payment.property_id:
        messages.error(
            request,
            "Assign this payment to a property before verification.",
        )
        return redirect("payment-list")

    if not visible_properties(request.user).filter(pk=payment.property_id).exists():
        messages.error(request, "You do not have access to this property's payments.")
        return redirect("payment-list")

    try:
        verified = verify_and_allocate(payment, request.user)
        unallocated = getattr(verified, "unallocated_amount", None)
        if unallocated is not None and unallocated > 0:
            messages.warning(
                request,
                "Payment matched and verified. "
                f"UGX {unallocated:,.0f} remains unallocated; "
                "record a controlled tenant credit or refund before using it."
            )
        else:
            messages.success(request, "Payment matched, verified and allocated.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("payment-list")
