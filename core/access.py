from properties.models import Property


def _active_profile(user):
    profile = getattr(user, "staff_profile", None)
    return profile if profile and profile.is_active else None


def is_manager(user):
    """Return whether an authenticated, active account has manager privileges."""
    if not user.is_authenticated or not user.is_active:
        return False

    profile = getattr(user, "staff_profile", None)
    # A disabled staff profile must not retain access through is_staff.
    if profile is not None and not profile.is_active:
        return False

    return bool(
        user.is_superuser
        or user.is_staff
        or (profile and profile.role == "MANAGER")
    )


def visible_properties(user):
    """Properties an active account is allowed to view."""
    if not user.is_authenticated or not user.is_active:
        return Property.objects.none()

    profile = getattr(user, "staff_profile", None)
    if profile is not None and not profile.is_active:
        return Property.objects.none()

    if is_manager(user):
        return Property.objects.all()

    return Property.objects.filter(assignments__staff=user).distinct()
