from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from payments.models import BankTransaction, Payment, PaymentAllocation
from payments.services import verify_and_allocate
from properties.models import Landlord, Property, Unit
from rent.models import RentCharge
from tenants.models import Tenant, Tenancy


class PaymentVerificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="payment-manager",
            password="test-password",
            is_staff=True,
        )
        landlord = Landlord.objects.create(full_name="Test Landlord")
        self.property = Property.objects.create(
            landlord=landlord,
            name="Test property",
            address="Kampala",
        )
        unit = Unit.objects.create(
            property=self.property,
            unit_number="A1",
            monthly_rent=Decimal("100000"),
            status="OCCUPIED",
        )
        self.tenant = Tenant.objects.create(full_name="Test Tenant")
        tenancy = Tenancy.objects.create(
            tenant=self.tenant,
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
            tenant=self.tenant,
            property=self.property,
            amount=Decimal("100000"),
            bank_reference="EQ-REF-001",
            status="PENDING",
        )

    def add_bank_transaction(self, amount=Decimal("100000")):
        return BankTransaction.objects.create(
            bank_reference=self.payment.bank_reference,
            transaction_date=timezone.now(),
            amount=amount,
            narrative="Test incoming transfer",
        )

    def test_payment_cannot_be_verified_without_bank_transaction(self):
        with self.assertRaisesMessage(ValueError, "No imported bank transaction"):
            verify_and_allocate(self.payment, self.user)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "PENDING")
        self.assertEqual(PaymentAllocation.objects.count(), 0)

    def test_payment_amount_must_match_bank_transaction(self):
        self.add_bank_transaction(Decimal("99000"))

        with self.assertRaisesMessage(ValueError, "amount does not match"):
            verify_and_allocate(self.payment, self.user)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "PENDING")
        self.assertEqual(PaymentAllocation.objects.count(), 0)

    def test_matching_payment_is_verified_allocated_and_reconciled(self):
        bank_transaction = self.add_bank_transaction()

        verified = verify_and_allocate(self.payment, self.user)

        self.payment.refresh_from_db()
        bank_transaction.refresh_from_db()
        self.charge.refresh_from_db()
        self.assertEqual(self.payment.status, "VERIFIED")
        self.assertEqual(self.payment.verified_by, self.user)
        self.assertEqual(self.charge.status, "PAID")
        self.assertEqual(self.charge.amount_paid, Decimal("100000.00"))
        self.assertEqual(bank_transaction.matched_payment, self.payment)
        self.assertEqual(bank_transaction.reconciliation_status, "MATCHED")
        self.assertEqual(PaymentAllocation.objects.count(), 1)
        self.assertEqual(verified.unallocated_amount, Decimal("0.00"))

    def test_overpayment_is_not_silently_allocated(self):
        self.payment.amount = Decimal("120000")
        self.payment.save(update_fields=["amount"])
        self.add_bank_transaction(Decimal("120000"))

        verified = verify_and_allocate(self.payment, self.user)

        self.assertEqual(verified.unallocated_amount, Decimal("20000.00"))
        self.assertEqual(self.charge.amount_paid, Decimal("100000.00"))

    def test_payment_only_allocates_to_its_selected_property(self):
        other_property = Property.objects.create(
            landlord=self.property.landlord,
            name="Other property",
            address="Other Kampala address",
        )
        other_unit = Unit.objects.create(
            property=other_property,
            unit_number="B1",
            monthly_rent=Decimal("100000"),
            status="OCCUPIED",
        )
        other_tenancy = Tenancy.objects.create(
            tenant=self.tenant,
            unit=other_unit,
            start_date=date(2026, 1, 1),
            monthly_rent=Decimal("100000"),
            status="ACTIVE",
        )
        other_charge = RentCharge.objects.create(
            tenancy=other_tenancy,
            billing_month=date(2026, 1, 1),
            amount=Decimal("100000"),
            due_date=date(2026, 1, 6),
        )

        self.payment.amount = Decimal("120000")
        self.payment.save(update_fields=["amount"])
        self.add_bank_transaction(Decimal("120000"))
        verified = verify_and_allocate(self.payment, self.user)

        self.charge.refresh_from_db()
        other_charge.refresh_from_db()
        self.assertEqual(self.charge.amount_paid, Decimal("100000.00"))
        self.assertEqual(other_charge.amount_paid, Decimal("0.00"))
        self.assertEqual(verified.unallocated_amount, Decimal("20000.00"))

    def test_unassigned_payment_cannot_be_verified(self):
        self.payment.property = None
        self.payment.save(update_fields=["property"])
        self.add_bank_transaction()

        with self.assertRaisesMessage(ValueError, "Assign this payment to a property"):
            verify_and_allocate(self.payment, self.user)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "PENDING")

    def test_verified_payment_is_idempotent(self):
        self.add_bank_transaction()
        verify_and_allocate(self.payment, self.user)
        verify_and_allocate(self.payment, self.user)

        self.assertEqual(PaymentAllocation.objects.count(), 1)
