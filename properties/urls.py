from django.urls import path
from . import views
urlpatterns=[path("",views.property_list,name="property-list"),path("new/",views.property_create,name="property-create"),path("units/new/",views.unit_create,name="unit-create")]
