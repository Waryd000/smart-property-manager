from django.urls import path
from . import views
urlpatterns=[path("",views.payment_list,name="payment-list"),path("<int:pk>/verify/",views.verify_payment,name="verify-payment")]
