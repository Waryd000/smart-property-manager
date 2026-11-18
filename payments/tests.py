from django.test import TestCase
from decimal import Decimal
from payments.models import Payment

class PaymentModelTests(TestCase):
    def test_bank_reference_is_required_and_unique(self):
        self.assertTrue(Payment._meta.get_field("bank_reference").unique)
