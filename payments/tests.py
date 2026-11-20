from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from payments.models import BankTransaction, Payment, PaymentAllocation
from payments.services import import_equity_statement_row, verify_and_allocate
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
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.unallocated_amount, Decimal("20000.00"))
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
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.unallocated_amount, Decimal("20000.00"))

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


    def test_payment_tenant_must_have_a_tenancy_in_selected_property(self):
        other_property = Property.objects.create(
            landlord=self.property.landlord,
            name="Unrelated property",
            address="Kampala",
        )
        self.payment.property = other_property
        self.payment.save(update_fields=["property"])
        self.add_bank_transaction()

        with self.assertRaisesMessage(ValueError, "no tenancy in this property"):
            verify_and_allocate(self.payment, self.user)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "PENDING")
        self.assertEqual(PaymentAllocation.objects.count(), 0)

    def test_bank_statement_import_is_idempotent_for_identical_row(self):
        row = {
            "reference": "EQ-STATEMENT-001",
            "transaction_date": timezone.now().isoformat(),
            "amount": "150000.00",
            "narrative": "Incoming tenant payment",
        }

        first, first_created = import_equity_statement_row(row)
        second, second_created = import_equity_statement_row(row)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)

    def test_bank_statement_import_rejects_conflicting_duplicate_reference(self):
        transaction_date = timezone.now().isoformat()
        import_equity_statement_row({
            "reference": "EQ-STATEMENT-CONFLICT",
            "transaction_date": transaction_date,
            "amount": "150000.00",
        })

        with self.assertRaisesMessage(ValueError, "different amount or date"):
            import_equity_statement_row({
                "reference": "EQ-STATEMENT-CONFLICT",
                "transaction_date": transaction_date,
                "amount": "175000.00",
            })

    def test_bank_statement_import_rejects_debit_or_zero_amount(self):
        with self.assertRaisesMessage(ValueError, "positive incoming"):
            import_equity_statement_row({
                "reference": "EQ-DEBIT-001",
                "transaction_date": timezone.now().isoformat(),
                "amount": "-10000.00",
            })


class BankStatementImportViewTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username="statement-manager",
            password="test-password",
            is_staff=True,
        )
        self.url = reverse("bank-statement-import")

    def upload(self, content, filename="equity-incoming.csv"):
        return SimpleUploadedFile(
            filename,
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_manager_can_import_normalized_incoming_csv(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            self.url,
            {
                "statement_file": self.upload(
                    "reference,transaction_date,amount,narrative\\n"
                    "EQ-UP-001,2026-11-20T10:15:00+03:00,250000,Incoming rent"
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BankTransaction.objects.count(), 1)
        tx = BankTransaction.objects.get(bank_reference="EQ-UP-001")
        self.assertEqual(tx.amount, Decimal("250000"))
        self.assertEqual(tx.reconciliation_status, "UNMATCHED")

    def test_identical_statement_upload_is_idempotent(self):
        self.client.force_login(self.manager)
        content = (
            "reference,transaction_date,amount,narrative\\n"
            "EQ-UP-002,2026-11-20T10:15:00+03:00,175000,Incoming rent"
        )
        self.client.post(self.url, {"statement_file": self.upload(content)})
        response = self.client.post(self.url, {"statement_file": self.upload(content)})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            BankTransaction.objects.filter(bank_reference="EQ-UP-002").count(),
            1,
        )

    def test_invalid_row_rolls_back_entire_statement(self):
        self.client.force_login(self.manager)
        content = (
            "reference,transaction_date,amount,narrative\\n"
            "EQ-GOOD-003,2026-11-20T10:15:00+03:00,125000,Good credit\\n"
            "EQ-DEBIT-003,2026-11-20T10:16:00+03:00,-5000,Debit"
        )
        response = self.client.post(
            self.url,
            {"statement_file": self.upload(content)},
            follow=True,
        )

        self.assertEqual(BankTransaction.objects.count(), 0)
        self.assertContains(response, "positive incoming")

    def test_missing_csv_headers_are_rejected(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            self.url,
            {
                "statement_file": self.upload(
                    "reference,amount\\nEQ-MISSING-DATE,50000"
                ),
            },
            follow=True,
        )

        self.assertEqual(BankTransaction.objects.count(), 0)
        self.assertContains(response, "Missing required CSV columns")

    def test_only_managers_can_import_bank_statements(self):
        staff = get_user_model().objects.create_user(
            username="ordinary-user",
            password="test-password",
            is_staff=False,
        )
        self.client.force_login(staff)
        response = self.client.post(
            self.url,
            {
                "statement_file": self.upload(
                    "reference,transaction_date,amount\\n"
                    "EQ-NO-ACCESS,2026-11-20T10:15:00+03:00,50000"
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BankTransaction.objects.count(), 0)
