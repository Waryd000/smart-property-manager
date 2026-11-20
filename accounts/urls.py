from django.urls import path

from . import views

urlpatterns = [
    path("", views.staff_list, name="staff-list"),
    path("new/", views.staff_create, name="staff-create"),
    path("<int:pk>/edit/", views.staff_update, name="staff-update"),
]
