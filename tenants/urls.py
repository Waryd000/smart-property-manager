from django.urls import path

from . import views

urlpatterns = [
    path("", views.tenant_list, name="tenant-list"),
    path("new/", views.tenant_create, name="tenant-create"),
    path("tenancies/new/", views.tenancy_create, name="tenancy-create"),
    path("tenancies/<int:pk>/confirm/", views.tenancy_confirm, name="tenancy-confirm"),
    path("tenancies/<int:pk>/end/", views.tenancy_end, name="tenancy-end"),
    path("tenancies/<int:pk>/agreement/", views.tenancy_agreement_download, name="tenancy-agreement-download"),
]
