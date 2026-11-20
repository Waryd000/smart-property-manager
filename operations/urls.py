from django.urls import path

from . import views

urlpatterns = [
    path("maintenance/", views.maintenance_list, name="maintenance-list"),
    path("maintenance/new/", views.maintenance_create, name="maintenance-create"),
    path("maintenance/<int:pk>/status/", views.maintenance_transition, name="maintenance-transition"),
    path("expenses/", views.expense_list, name="expense-list"),
    path("expenses/new/", views.expense_create, name="expense-create"),
    path("expenses/<int:pk>/status/", views.expense_transition, name="expense-transition"),
]
