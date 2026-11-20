from django.contrib import admin
from django.urls import include, path

from core.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", dashboard, name="dashboard"),
    path("properties/", include("properties.urls")),
    path("tenants/", include("tenants.urls")),
    path("rent/", include("rent.urls")),
    path("payments/", include("payments.urls")),
    path("operations/", include("operations.urls")),
]
