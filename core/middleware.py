from django.core.exceptions import PermissionDenied

from core.access import is_manager


class ManagerAdminAccessMiddleware:
    """Prevent ordinary StaffProfile accounts from using Django's global admin.

    The default Django admin checks is_staff, which is not sufficient for this
    application because an account may be is_staff for operational purposes.
    Only an active manager/superuser can use the global admin site.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith("/admin/")
            and request.user.is_authenticated
            and request.user.is_staff
            and not is_manager(request.user)
        ):
            raise PermissionDenied("Only managers can access administration.")
        return self.get_response(request)
