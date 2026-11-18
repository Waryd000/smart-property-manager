from django.test import TestCase
from datetime import date
from rent.services import safe_due_date
class RentDateTests(TestCase):
 def test_due_date_clamps_to_month_end(self): self.assertEqual(safe_due_date(2026,2,28),date(2026,2,28))
