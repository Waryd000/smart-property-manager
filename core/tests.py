from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import StaffProfile
from core.access import is_manager
from payments.models import Payment
from properties.models import Landlord, Property, PropertyAssignment, Unit
from rent.models import RentCharge
from rent.services import safe_due_date
from tenants.models import Tenant, Tenancy


class RentDateTests(TestCase):
    def test_due_date_clamps_to_month_end(self):
        self.assertEqual(safe_due_date(2026, 2, 28), date(2026, 2, 28))


class DashboardPortfolioAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="assigned-staff",
            password="test-password",
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)

        self.manager = User.objects.create_user(
            username="manager",
            password="test-password",
            is_staff=True,
        )

        self.landlord = Landlord.objects.create(full_name="Test Landlord")
        self.assigned_property, self.assigned_tenant = self._make_property(
            "Assigned property", "A1", "Assigned tenant", "REVIEW: Confirm source record"
        )
        self.other_property, self.other_tenant = self._make_property(
            "Other property", "B1", "Other tenant", ""
        )
        PropertyAssignment.objects.create(
            property=self.assigned_property,
            staff=self.staff,
        )

    def _make_property(self, property_name, unit_number, tenant_name, review_note):
        prop = Property.objects.create(
            landlord=self.landlord,
            name=property_name,
            address="Test address",
        )
        notes = f"Source: test register. {review_note}" if review_note else ""
        unit = Unit.objects.create(
            property=prop,
            unit_number=unit_number,
            monthly_rent=Decimal("100000"),
            status="OCCUPIED",
            notes=notes,
        )
        tenant = Tenant.objects.create(full_name=tenant_name)
        tenancy = Tenancy.objects.create(
            tenant=tenant,
            unit=unit,
            start_date=timezone.localdate(),
            monthly_rent=Decimal("100000"),
            status="ACTIVE",
        )
        RentCharge.objects.create(
            tenancy=tenancy,
            billing_month=timezone.localdate().replace(day=1),
            amount=Decimal("100000"),
            due_date=timezone.localdate(),
        )
        Payment.objects.create(
            tenant=tenant,
            property=prop,
            amount=Decimal("100000"),
            bank_reference=f"TEST-{unit_number}",
            status="VERIFIED",
            verified_at=timezone.now(),
        )
        return prop, tenant

    def test_staff_dashboard_only_includes_assigned_property_data(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["property_count"], 1)
        self.assertEqual(response.context["unit_count"], 1)
        self.assertEqual(response.context["occupied_count"], 1)
        self.assertEqual(response.context["tenant_count"], 1)
        self.assertEqual(response.context["outstanding"], Decimal("100000.00"))
        self.assertEqual(response.context["overdue_count"], 0)
        self.assertEqual(len(response.context["recent_payments"]), 1)
        self.assertEqual(len(response.context["spreadsheet_review_flags"]), 1)
        self.assertEqual(
            response.context["spreadsheet_review_flags"][0]["property"],
            "Assigned property",
        )

    def test_manager_dashboard_includes_all_properties(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["property_count"], 2)
        self.assertEqual(response.context["unit_count"], 2)
        self.assertEqual(response.context["tenant_count"], 2)
        self.assertEqual(len(response.context["recent_payments"]), 2)
        self.assertEqual(len(response.context["spreadsheet_review_flags"]), 1)

    def test_inactive_staff_profile_cannot_retain_property_access(self):
        inactive_staff = get_user_model().objects.create_user(
            username="inactive-staff",
            password="test-password",
            is_staff=True,
        )
        StaffProfile.objects.create(
            user=inactive_staff,
            role="MANAGER",
            is_active=False,
        )
        PropertyAssignment.objects.create(
            property=self.assigned_property,
            staff=inactive_staff,
        )

        self.client.force_login(inactive_staff)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["property_count"], 0)
        self.assertEqual(response.context["unit_count"], 0)
        self.assertEqual(response.context["tenant_count"], 0)
        self.assertEqual(response.context["outstanding"], Decimal("0.00"))
        self.assertEqual(len(response.context["recent_payments"]), 0)
        self.assertEqual(len(response.context["spreadsheet_review_flags"]), 0)

    def test_staff_profile_role_overrides_django_is_staff_flag(self):
        elevated_staff = get_user_model().objects.create_user(
            username="role-staff",
            password="test-password",
            is_staff=True,
        )
        StaffProfile.objects.create(user=elevated_staff, role="STAFF", is_active=True)

        self.assertFalse(is_manager(elevated_staff))

    def test_staff_profile_role_cannot_access_global_admin(self):
        elevated_staff = get_user_model().objects.create_user(
            username="blocked-admin",
            password="test-password",
            is_staff=True,
        )
        StaffProfile.objects.create(user=elevated_staff, role="STAFF", is_active=True)
        self.client.force_login(elevated_staff)

        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 403)

    def test_profile_manager_can_use_manager_features_without_django_is_staff(self):
        profile_manager = get_user_model().objects.create_user(
            username="profile-manager",
            password="test-password",
            is_staff=False,
        )
        StaffProfile.objects.create(user=profile_manager, role="MANAGER", is_active=True)

        self.assertTrue(is_manager(profile_manager))
        self.assertEqual(
            list(__import__("core.access", fromlist=["visible_properties"]).visible_properties(profile_manager)),
            list(Property.objects.all()),
        )


class HealthCheckTests(TestCase):
    def test_health_check_returns_minimal_database_readiness(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})
