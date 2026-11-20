from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from properties.models import Landlord, Property, Unit
from tenants.models import Tenant, Tenancy


class TenancyIntegrityTests(TestCase):
    def setUp(self):
        landlord = Landlord.objects.create(full_name="Test Landlord")
        property_record = Property.objects.create(
            landlord=landlord,
            name="Test Property",
            address="Kampala",
        )
        self.unit = Unit.objects.create(
            property=property_record,
            unit_number="A1",
            monthly_rent=Decimal("250000"),
        )
        self.tenant = Tenant.objects.create(full_name="First Tenant")
        self.active_tenancy = Tenancy.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            start_date=date(2026, 1, 1),
            monthly_rent=Decimal("250000"),
            status="ACTIVE",
        )

    def build_tenancy(self, **overrides):
        defaults = {
            "tenant": Tenant.objects.create(full_name="Another Tenant"),
            "unit": self.unit,
            "start_date": date(2026, 2, 1),
            "monthly_rent": Decimal("250000"),
            "status": "PENDING",
        }
        defaults.update(overrides)
        return Tenancy(**defaults)

    def test_pending_tenancy_can_have_unknown_start_date(self):
        tenancy = self.build_tenancy(start_date=None, status="PENDING")
        tenancy.full_clean()
        tenancy.save()
        self.assertIsNone(tenancy.start_date)

    def test_active_tenancy_requires_confirmed_start_date(self):
        tenancy = self.build_tenancy(start_date=None, status="ACTIVE")
        with self.assertRaises(ValidationError) as raised:
            tenancy.full_clean()
        self.assertIn("start_date", raised.exception.message_dict)

    def test_end_date_cannot_precede_start_date(self):
        tenancy = self.build_tenancy(
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 9),
            status="ENDED",
        )
        with self.assertRaises(ValidationError) as raised:
            tenancy.full_clean()
        self.assertIn("end_date", raised.exception.message_dict)

    def test_only_one_active_tenancy_per_unit(self):
        tenancy = self.build_tenancy(status="ACTIVE")
        with self.assertRaises(ValidationError) as raised:
            tenancy.full_clean()
        self.assertIn("unit", raised.exception.message_dict)

    def test_database_constraint_blocks_second_active_tenancy(self):
        another_tenant = Tenant.objects.create(full_name="Third Tenant")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tenancy.objects.create(
                    tenant=another_tenant,
                    unit=self.unit,
                    start_date=date(2026, 4, 1),
                    monthly_rent=Decimal("250000"),
                    status="ACTIVE",
                )

    def test_new_active_tenancy_allowed_after_previous_tenancy_ends(self):
        self.active_tenancy.status = "ENDED"
        self.active_tenancy.end_date = date(2026, 2, 28)
        self.active_tenancy.save(update_fields=["status", "end_date", "updated_at"])

        new_tenancy = self.build_tenancy(status="ACTIVE", start_date=date(2026, 3, 1))
        new_tenancy.full_clean()
        new_tenancy.save()
        self.assertEqual(
            Tenancy.objects.filter(unit=self.unit, status="ACTIVE").count(),
            1,
        )
