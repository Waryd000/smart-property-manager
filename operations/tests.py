from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import StaffProfile
from operations.models import AuditLog, Expense, MaintenanceRequest
from properties.models import Landlord, Property, PropertyAssignment, Unit


class OperationsWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(
            username="operations-manager", password="test-password", is_staff=True
        )
        self.staff = User.objects.create_user(
            username="operations-staff", password="test-password", is_staff=True
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)

        landlord = Landlord.objects.create(full_name="Operations Landlord")
        self.property = Property.objects.create(
            landlord=landlord, name="Assigned Operations Property", address="Kampala"
        )
        self.other_property = Property.objects.create(
            landlord=landlord, name="Other Operations Property", address="Kampala"
        )
        self.unit = Unit.objects.create(
            property=self.property, unit_number="OP-1",
            monthly_rent=Decimal("250000"), status="OCCUPIED",
        )
        self.other_unit = Unit.objects.create(
            property=self.other_property, unit_number="OP-2",
            monthly_rent=Decimal("250000"), status="OCCUPIED",
        )
        PropertyAssignment.objects.create(property=self.property, staff=self.staff)

    def test_staff_can_submit_maintenance_for_assigned_property(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("maintenance-create"),
            {
                "property": self.property.pk,
                "unit": self.unit.pk,
                "description": "Leaking kitchen pipe",
                "priority": "HIGH",
                "estimated_cost": "85000.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        item = MaintenanceRequest.objects.get()
        self.assertEqual(item.status, "OPEN")
        self.assertEqual(item.reported_by, self.staff.username)
        self.assertTrue(AuditLog.objects.filter(
            action="MAINTENANCE_REQUEST_CREATED",
            record_id=str(item.pk),
        ).exists())

    def test_staff_cannot_submit_maintenance_for_unassigned_property(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("maintenance-create"),
            {
                "property": self.other_property.pk,
                "unit": self.other_unit.pk,
                "description": "Unauthorised property issue",
                "priority": "NORMAL",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MaintenanceRequest.objects.count(), 0)

    def test_staff_list_shows_only_assigned_property_maintenance(self):
        visible_item = MaintenanceRequest.objects.create(
            property=self.property, unit=self.unit, description="Visible", reported_by="Staff"
        )
        MaintenanceRequest.objects.create(
            property=self.other_property, unit=self.other_unit,
            description="Private property issue", reported_by="Other",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("maintenance-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["maintenance_requests"]), [visible_item])
        self.assertContains(response, "Visible")
        self.assertNotContains(response, "Private property issue")

    def test_only_manager_can_advance_maintenance_status(self):
        item = MaintenanceRequest.objects.create(
            property=self.property, unit=self.unit, description="Broken lock"
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("maintenance-transition", args=[item.pk]),
            {"status": "REVIEW"},
        )

        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, "OPEN")

    def test_maintenance_status_sequence_and_audit(self):
        item = MaintenanceRequest.objects.create(
            property=self.property, unit=self.unit, description="Broken gate"
        )
        self.client.force_login(self.manager)
        url = reverse("maintenance-transition", args=[item.pk])

        for status in ["REVIEW", "APPROVED", "IN_PROGRESS"]:
            response = self.client.post(url, {"status": status})
            self.assertEqual(response.status_code, 302)
            item.refresh_from_db()
            self.assertEqual(item.status, status)

        response = self.client.post(
            url, {"status": "COMPLETED", "actual_cost": "64000.00"}
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, "COMPLETED")
        self.assertEqual(item.actual_cost, Decimal("64000.00"))
        self.assertIsNotNone(item.completed_at)
        self.assertEqual(
            AuditLog.objects.filter(
                action="MAINTENANCE_STATUS_CHANGED",
                record_id=str(item.pk),
            ).count(),
            4,
        )

    def test_invalid_maintenance_transition_is_rejected(self):
        item = MaintenanceRequest.objects.create(
            property=self.property, description="Pending review"
        )
        self.client.force_login(self.manager)

        self.client.post(
            reverse("maintenance-transition", args=[item.pk]),
            {"status": "COMPLETED"},
        )

        item.refresh_from_db()
        self.assertEqual(item.status, "OPEN")

    def test_staff_can_submit_expense_as_pending(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("expense-create"),
            {
                "property": self.property.pk,
                "category": "Plumbing",
                "description": "Emergency pipe repair",
                "amount": "95000.00",
                "incurred_on": "2026-11-20",
            },
        )

        self.assertEqual(response.status_code, 302)
        item = Expense.objects.get()
        self.assertEqual(item.status, "PENDING")
        self.assertIsNone(item.approved_by)
        self.assertTrue(AuditLog.objects.filter(
            action="EXPENSE_SUBMITTED",
            record_id=str(item.pk),
        ).exists())

    def test_expense_cannot_be_submitted_for_unassigned_property(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("expense-create"),
            {
                "property": self.other_property.pk,
                "category": "Repairs",
                "description": "Other property",
                "amount": "50000",
                "incurred_on": "2026-11-20",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_staff_cannot_approve_or_pay_expenses(self):
        item = Expense.objects.create(
            property=self.property, category="Repair", description="Lock",
            amount=Decimal("10000"), incurred_on=date(2026, 11, 20),
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("expense-transition", args=[item.pk]), {"status": "APPROVED"}
        )

        item.refresh_from_db()
        self.assertEqual(item.status, "PENDING")
        self.assertIsNone(item.approved_by)

    def test_expense_requires_approval_before_payment(self):
        item = Expense.objects.create(
            property=self.property, category="Repair", description="Lock",
            amount=Decimal("10000"), incurred_on=date(2026, 11, 20),
        )
        self.client.force_login(self.manager)

        self.client.post(
            reverse("expense-transition", args=[item.pk]),
            {"status": "PAID", "payment_reference": "VOUCHER-001"},
        )

        item.refresh_from_db()
        self.assertEqual(item.status, "PENDING")
        self.assertEqual(item.payment_reference, "")

    def test_expense_payment_requires_reference_and_records_approver(self):
        item = Expense.objects.create(
            property=self.property, category="Repair", description="Lock",
            amount=Decimal("10000"), incurred_on=date(2026, 11, 20),
        )
        self.client.force_login(self.manager)
        url = reverse("expense-transition", args=[item.pk])

        self.client.post(url, {"status": "APPROVED"})
        item.refresh_from_db()
        self.assertEqual(item.status, "APPROVED")
        self.assertEqual(item.approved_by, self.manager)

        self.client.post(url, {"status": "PAID"})
        item.refresh_from_db()
        self.assertEqual(item.status, "APPROVED")
        self.assertEqual(item.payment_reference, "")

        self.client.post(
            url, {"status": "PAID", "payment_reference": "VOUCHER-2026-0042"}
        )
        item.refresh_from_db()
        self.assertEqual(item.status, "PAID")
        self.assertEqual(item.paid_by, self.manager)
        self.assertEqual(item.payment_reference, "VOUCHER-2026-0042")
        self.assertIsNotNone(item.paid_at)
        self.assertTrue(AuditLog.objects.filter(
            action="EXPENSE_STATUS_CHANGED",
            record_id=str(item.pk),
            details__to="PAID",
        ).exists())

    def test_staff_expense_list_is_property_scoped(self):
        visible = Expense.objects.create(
            property=self.property, category="Repair", description="Assigned expense",
            amount=Decimal("1000"), incurred_on=date(2026, 11, 20),
        )
        Expense.objects.create(
            property=self.other_property, category="Repair", description="Private expense",
            amount=Decimal("2000"), incurred_on=date(2026, 11, 20),
        )
        self.client.force_login(self.staff)
        response = self.client.get(reverse("expense-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["expenses"]), [visible])
        self.assertContains(response, "Assigned expense")
        self.assertNotContains(response, "Private expense")
