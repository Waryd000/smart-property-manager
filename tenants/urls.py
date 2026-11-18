from django.urls import path
from . import views
urlpatterns=[path("",views.tenant_list,name="tenant-list"),path("new/",views.tenant_create,name="tenant-create"),path("tenancies/new/",views.tenancy_create,name="tenancy-create")]
