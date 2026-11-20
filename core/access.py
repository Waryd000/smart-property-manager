from django.core.exceptions import ObjectDoesNotExist

from properties.models import Property


def staff_profile_for(user):
    """Safely return a user's optional StaffProfile."""
    try:
        return user.staff_profile
    except ObjectDoesNotExist:
        return None


def is_manager(user):
    """Return whether an authenticated, active account has manager privileges.

    When a StaffProfile exists, its role is authoritative. Django's is_staff
    flag alone must not promote an ordinary property staff member to manager.
    Accounts without a StaffProfile retain legacy superuser/admin behavior.
    """
    if not user.is_authenticated or not user.is_active:
        return False

    profile = staff_profile_for(user)
    if profile is not None:
        if not profile.is_active:
            return False
        return bool(user.is_superuser or profile.role == "MANAGER")

    return bool(user.is_superuser or user.is_staff)


def visible_properties(user):
    """Return only properties this active account is allowed to access."""
    if not user.is_authenticated or not user.is_active:
        return Property.objects.none()

    profile = staff_profile_for(user)
    if profile is not None and not profile.is_active:
        return Property.objects.none()

    if is_manager(user):
        return Property.objects.all()

    return Property.objects.filter(assignments__staff=user).distinct()
