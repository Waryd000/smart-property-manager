from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import StaffProfile
from operations.models import AuditLog
from payments.models import BankTransaction, Payment, PaymentAllocation
from payments.services import reverse_verified_payment, verify_and_allocate
from properties.models import Landlord, Property, Unit
from rent.models import RentCharge
from tenants.models import Tenant, Tenancy


class PaymentReversalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(
            username="reversal-manager",
            password="test-password",
            is_staff=True,
        )
        self.staff = User.objects.create_user(
            username="reversal-staff",
            password="test-password",
            is_staff=True,
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)

        landlord = Landlord.objects.create(full_name="Reversal Landlord")
        self.property = Property.objects.create(
            landlord=landlord,
            name="Reversal Property",
            address="Kampala",
        )
        unit = Unit.objects.create(
            property=self.property,
            unit_number="REV-1",
            monthly_rent=Decimal("100000"),
            status="OCCUPIED",
        )
        tenant = Tenant.objects.create(full_name="Reversal Tenant")
        tenancy = Tenancy.objects.create(
            tenant=tenant,
            unit=unit,
            start_date=date(2026, 1, 1),
            monthly_rent=Decimal("100000"),
            status="ACTIVE",
        )
        self.charge = RentCharge.objects.create(
            tenancy=tenancy,
            billing_month=date(2026, 1, 1),
            amount=Decimal("100000"),
            due_date=date(2026, 1, 5),
        )
        self.payment = Payment.objects.create(
            tenant=tenant,
            property=self.property,
            amount=Decimal("100000"),
            bank_reference="EQ-REVERSAL-001",
            status="PENDING",
        )
        self.bank_transaction = BankTransaction.objects.create(
            bank_reference="EQ-REVERSAL-001",
            transaction_date=timezone.now(),
            amount=Decimal("100000"),
        )
        verify_and_allocate(self.payment, self.manager)
        self.payment.refresh_from_db()
        self.charge.refresh_from_db()

    def test_manager_reversal_restores_rent_balance_and_preserves_history(self):
        reversed_payment = reverse_verified_payment(
            self.payment,
            self.manager,
            "Bank transaction was matched to the wrong tenant account.",
        )

        self.charge.refresh_from_db()
        self.payment.refresh_from_db()
        self.bank_transaction.refresh_from_db()
        allocation = PaymentAllocation.objects.get(payment=self.payment)

        self.assertEqual(reversed_payment.status, "REVERSED")
        self.assertEqual(self.payment.status, "REVERSED")
        self.assertIsNotNone(self.payment.reversed_at)
        self.assertEqual(self.payment.reversed_by, self.manager)
        self.assertIn("wrong tenant", self.payment.reversal_reason)
        self.assertEqual(self.charge.amount_paid, Decimal("0.00"))
        self.assertEqual(self.charge.balance, Decimal("100000.00"))
        self.assertEqual(self.charge.status, "OVERDUE")
        self.assertEqual(PaymentAllocation.objects.filter(payment=self.payment).count(), 1)
        self.assertIsNotNone(allocation.reversed_at)
        self.assertEqual(allocation.reversed_by, self.manager)
        self.assertEqual(self.bank_transaction.reconciliation_status, "REVERSED")
        self.assertEqual(self.bank_transaction.matched_payment, self.payment)
        self.assertTrue(AuditLog.objects.filter(
            action="PAYMENT_REVERSED",
            model_name="Payment",
            record_id=str(self.payment.pk),
        ).exists())

    def test_staff_cannot_reverse_even_when_django_is_staff(self):
        with self.assertRaisesMessage(ValueError, "Only an active manager"):
            reverse_verified_payment(
                self.payment,
                self.staff,
                "Not permitted",
            )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "VERIFIED")
        self.assertEqual(self.charge.amount_paid, Decimal("100000.00"))

    def test_reversal_reason_is_mandatory(self):
        with self.assertRaisesMessage(ValueError, "reason is required"):
            reverse_verified_payment(self.payment, self.manager, "  ")

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "VERIFIED")

    def test_reversal_cannot_be_applied_twice(self):
        reverse_verified_payment(self.payment, self.manager, "Incorrect payment entry.")
        with self.assertRaisesMessage(ValueError, "Only verified payments"):
            reverse_verified_payment(self.payment, self.manager, "Second reversal")
        self.assertEqual(
            PaymentAllocation.objects.filter(
                payment=self.payment,
                reversed_at__isnull=False,
            ).count(),
            1,
        )

    def test_pending_payment_cannot_be_reversed(self):
        pending = Payment.objects.create(
            tenant=self.payment.tenant,
            property=self.property,
            amount=Decimal("10000"),
            bank_reference="EQ-PENDING-REVERSAL",
            status="PENDING",
        )
        with self.assertRaisesMessage(ValueError, "Only verified payments"):
            reverse_verified_payment(pending, self.manager, "Wrongly entered")
