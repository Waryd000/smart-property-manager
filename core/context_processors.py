from core.access import is_manager


def role_flags(request):
    """Expose a safe role flag for shared navigation and presentation."""
    return {"is_manager_account": is_manager(request.user)}
