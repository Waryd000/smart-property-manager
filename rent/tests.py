from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import StaffProfile
from properties.models import Landlord, Property, PropertyAssignment, Unit
from rent.models import RentCharge
from rent.services import generate_monthly_charges, safe_due_date
from tenants.models import Tenant, Tenancy


class RentGenerationTests(TestCase):
    def setUp(self):
        self.landlord = Landlord.objects.create(full_name="Rent Test Landlord")
        self.property = Property.objects.create(
            landlord=self.landlord,
            name="Rent Test Property",
            address="Kampala",
        )
        self.unit = Unit.objects.create(
            property=self.property,
            unit_number="R1",
            monthly_rent=Decimal("200000"),
            status="OCCUPIED",
        )
        self.tenant = Tenant.objects.create(full_name="Rent Test Tenant")

    def make_tenancy(self, **overrides):
        values = {
            "tenant": self.tenant,
            "unit": self.unit,
            "start_date": date(2026, 11, 10),
            "monthly_rent": Decimal("200000"),
            "due_day": 5,
            "status": "ACTIVE",
        }
        values.update(overrides)
        return Tenancy.objects.create(**values)

    def test_monthly_generator_creates_charge_for_active_tenancy(self):
        tenancy = self.make_tenancy()

        charges = generate_monthly_charges(date(2026, 11, 20))

        self.assertEqual(len(charges), 1)
        self.assertEqual(charges[0].tenancy, tenancy)
        self.assertEqual(charges[0].billing_month, date(2026, 11, 1))
        self.assertEqual(charges[0].due_date, date(2026, 11, 5))
        self.assertEqual(charges[0].amount, Decimal("200000"))

    def test_generation_is_idempotent_for_calendar_month(self):
        self.make_tenancy()

        first = generate_monthly_charges("2026-11-01")
        second = generate_monthly_charges(date(2026, 11, 28))

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(RentCharge.objects.count(), 1)

    def test_pending_and_ended_tenancies_are_not_charged(self):
        self.make_tenancy(status="PENDING")
        other_tenant = Tenant.objects.create(full_name="Ended Tenant")
        other_unit = Unit.objects.create(
            property=self.property,
            unit_number="R2",
            monthly_rent=Decimal("180000"),
            status="VACANT",
        )
        Tenancy.objects.create(
            tenant=other_tenant,
            unit=other_unit,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 10, 31),
            monthly_rent=Decimal("180000"),
            status="ENDED",
        )

        charges = generate_monthly_charges(date(2026, 11, 1))

        self.assertEqual(charges, [])
        self.assertEqual(RentCharge.objects.count(), 0)

    def test_future_tenancy_is_not_charged_early(self):
        self.make_tenancy(start_date=date(2026, 12, 1))

        charges = generate_monthly_charges(date(2026, 11, 1))

        self.assertEqual(charges, [])
        self.assertEqual(RentCharge.objects.count(), 0)

    def test_due_date_clamps_to_february_month_end(self):
        self.assertEqual(safe_due_date(2024, 2, 31), date(2024, 2, 29))
        self.assertEqual(safe_due_date(2026, 2, 31), date(2026, 2, 28))

    def test_invalid_billing_month_string_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "valid ISO date"):
            generate_monthly_charges("not-a-date")


class RentPortfolioVisibilityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="rent-view-staff",
            password="test-password",
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)
        landlord = Landlord.objects.create(full_name="Rent Visibility Landlord")
        self.assigned_property = Property.objects.create(
            landlord=landlord,
            name="Assigned Rent Property",
            address="Kampala",
        )
        self.other_property = Property.objects.create(
            landlord=landlord,
            name="Other Rent Property",
            address="Kampala",
        )
        self.assigned_charge = self.create_charge(self.assigned_property, "R-A")
        self.other_charge = self.create_charge(self.other_property, "R-B")
        PropertyAssignment.objects.create(
            property=self.assigned_property,
            staff=self.staff,
        )

    def create_charge(self, property_record, unit_number):
        unit = Unit.objects.create(
            property=property_record,
            unit_number=unit_number,
            monthly_rent=Decimal("150000"),
            status="OCCUPIED",
        )
        tenant = Tenant.objects.create(full_name=f"Tenant {unit_number}")
        tenancy = Tenancy.objects.create(
            tenant=tenant,
            unit=unit,
            start_date=date(2026, 1, 1),
            monthly_rent=Decimal("150000"),
            status="ACTIVE",
        )
        return RentCharge.objects.create(
            tenancy=tenancy,
            billing_month=date(2026, 1, 1),
            amount=Decimal("150000"),
            due_date=date(2026, 1, 5),
        )

    def test_staff_rent_register_only_shows_assigned_property(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("rent-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["charges"]), [self.assigned_charge])
        self.assertContains(response, "Assigned Rent Property")
        self.assertNotContains(response, "Other Rent Property")

    def test_rent_register_calculates_overdue_display_from_today(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("rent-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today"], timezone.localdate())
