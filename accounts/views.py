from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from core.access import is_manager
from properties.models import PropertyAssignment
from .forms import StaffCreateForm, StaffUpdateForm
from .models import StaffProfile


@login_required
def staff_list(request):
    if not is_manager(request.user):
        messages.error(request, "Only managers can administer staff accounts.")
        return redirect("dashboard")

    profiles = StaffProfile.objects.select_related("user").prefetch_related(
        "user__property_assignments__property"
    )
    if not request.user.is_superuser:
        profiles = profiles.exclude(user__is_superuser=True).exclude(role="MANAGER")
    return render(request, "accounts/staff_list.html", {"profiles": profiles})


@login_required
def staff_create(request):
    if not is_manager(request.user):
        messages.error(request, "Only managers can create staff accounts.")
        return redirect("dashboard")

    form = StaffCreateForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        User = get_user_model()
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["username"],
                password=data["password1"],
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                email=data.get("email", ""),
                is_active=True,
                is_staff=True,
            )
            profile = StaffProfile.objects.create(
                user=user,
                phone=data.get("phone", ""),
                role=data["role"],
                is_active=True,
            )
            PropertyAssignment.objects.bulk_create([
                PropertyAssignment(property=prop, staff=user)
                for prop in data["properties"]
            ])
        messages.success(request, f"Staff account {user.username} created.")
        return redirect("staff-list")

    return render(
        request,
        "accounts/staff_form.html",
        {"form": form, "title": "Create staff account"},
    )


@login_required
def staff_update(request, pk):
    if not is_manager(request.user):
        messages.error(request, "Only managers can update staff accounts.")
        return redirect("dashboard")

    profile_qs = StaffProfile.objects.select_related("user").prefetch_related(
        "user__property_assignments"
    )
    if not request.user.is_superuser:
        profile_qs = profile_qs.exclude(user__is_superuser=True).exclude(role="MANAGER")
    profile = get_object_or_404(profile_qs, pk=pk)

    initial = {
        "first_name": profile.user.first_name,
        "last_name": profile.user.last_name,
        "email": profile.user.email,
        "phone": profile.phone,
        "role": profile.role,
        "is_active": profile.is_active and profile.user.is_active,
        "properties": profile.user.property_assignments.values_list(
            "property_id", flat=True
        ),
    }
    form = StaffUpdateForm(
        request.POST or None,
        actor=request.user,
        profile=profile,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = profile.user
            user.first_name = data["first_name"]
            user.last_name = data["last_name"]
            user.email = data["email"]
            user.is_active = data["is_active"]
            user.save(update_fields=["first_name", "last_name", "email", "is_active"])

            profile.phone = data["phone"]
            profile.is_active = data["is_active"]
            if request.user.is_superuser:
                profile.role = data["role"]
            profile.save(update_fields=["phone", "is_active", "role", "updated_at"])

            PropertyAssignment.objects.filter(staff=user).delete()
            PropertyAssignment.objects.bulk_create([
                PropertyAssignment(property=prop, staff=user)
                for prop in data["properties"]
            ])

        messages.success(request, f"Staff account {user.username} updated.")
        return redirect("staff-list")

    return render(
        request,
        "accounts/staff_form.html",
        {
            "form": form,
            "title": f"Update staff account: {profile.user.username}",
            "profile": profile,
        },
    )
