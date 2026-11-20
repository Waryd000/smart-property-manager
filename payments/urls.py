from django.urls import path
from . import views

urlpatterns = [
    path("", views.payment_list, name="payment-list"),
    path("bank-import/", views.bank_statement_import, name="bank-statement-import"),
    path("<int:pk>/verify/", views.verify_payment, name="verify-payment"),
]
