from django.urls import path
from .views import rent_list
urlpatterns=[path("",rent_list,name="rent-list")]
