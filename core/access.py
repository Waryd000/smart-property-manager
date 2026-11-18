from properties.models import Property

def is_manager(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    profile = getattr(user, "staff_profile", None)
    return bool(profile and profile.is_active and profile.role == "MANAGER")

def visible_properties(user):
    qs = Property.objects.all()
    if is_manager(user):
        return qs
    if not user.is_authenticated:
        return qs.none()
    return qs.filter(assignments__staff=user).distinct()
