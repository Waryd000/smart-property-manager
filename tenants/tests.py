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

    def test_database_constraint_rejects_active_tenancy_without_start_date(self):
        tenant = Tenant.objects.create(full_name="No Date Tenant")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tenancy.objects.create(
                    tenant=tenant,
                    unit=Unit.objects.create(
                        property=self.unit.property,
                        unit_number="A2",
                        monthly_rent=Decimal("250000"),
                    ),
                    start_date=None,
                    monthly_rent=Decimal("250000"),
                    status="ACTIVE",
                )

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


class TenantPortfolioVisibilityTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        from accounts.models import StaffProfile
        from properties.models import PropertyAssignment

        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="property-staff",
            password="test-password",
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)

        landlord = Landlord.objects.create(full_name="Portfolio Landlord")
        self.assigned_property = Property.objects.create(
            landlord=landlord,
            name="Assigned Property",
            address="Kampala",
        )
        self.other_property = Property.objects.create(
            landlord=landlord,
            name="Other Property",
            address="Kampala",
        )
        self.assigned_unit = Unit.objects.create(
            property=self.assigned_property,
            unit_number="A1",
            monthly_rent=Decimal("250000"),
        )
        self.other_unit = Unit.objects.create(
            property=self.other_property,
            unit_number="B1",
            monthly_rent=Decimal("250000"),
        )
        tenant = Tenant.objects.create(full_name="Shared Tenant")
        Tenancy.objects.create(
            tenant=tenant,
            unit=self.assigned_unit,
            start_date=date(2026, 1, 1),
            monthly_rent=Decimal("250000"),
            status="ACTIVE",
        )
        Tenancy.objects.create(
            tenant=tenant,
            unit=self.other_unit,
            start_date=date(2026, 1, 1),
            monthly_rent=Decimal("250000"),
            status="ACTIVE",
        )
        PropertyAssignment.objects.create(
            property=self.assigned_property,
            staff=self.staff,
        )

    def test_staff_only_sees_tenancies_on_assigned_properties(self):
        from django.urls import reverse

        self.client.force_login(self.staff)
        response = self.client.get(reverse("tenant-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["tenants"]), 1)
        tenant = response.context["tenants"][0]
        visible_tenancies = list(tenant.tenancies.all())
        self.assertEqual(len(visible_tenancies), 1)
        self.assertEqual(visible_tenancies[0].unit, self.assigned_unit)


class TenantCreationScopeTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from accounts.models import StaffProfile
        from properties.models import PropertyAssignment

        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="tenant-creator",
            password="test-password",
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)

        landlord = Landlord.objects.create(full_name="Creation Landlord")
        self.allowed_property = Property.objects.create(
            landlord=landlord,
            name="Allowed Property",
            address="Kampala",
        )
        self.other_property = Property.objects.create(
            landlord=landlord,
            name="Other Property",
            address="Kampala",
        )
        self.allowed_unit = Unit.objects.create(
            property=self.allowed_property,
            unit_number="C1",
            monthly_rent=Decimal("180000"),
        )
        self.other_tenant = Tenant.objects.create(full_name="Other Portfolio Tenant")
        other_unit = Unit.objects.create(
            property=self.other_property,
            unit_number="D1",
            monthly_rent=Decimal("180000"),
        )
        Tenancy.objects.create(
            tenant=self.other_tenant,
            unit=other_unit,
            start_date=date(2026, 1, 1),
            monthly_rent=Decimal("180000"),
            status="ACTIVE",
        )
        PropertyAssignment.objects.create(
            property=self.allowed_property,
            staff=self.staff,
        )

    def test_new_tenant_profile_is_owned_by_creator_and_visible_without_tenancy(self):
        from django.urls import reverse

        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("tenant-create"),
            {"full_name": "New Staff Tenant"},
        )

        self.assertEqual(response.status_code, 302)
        tenant = Tenant.objects.get(full_name="New Staff Tenant")
        self.assertEqual(tenant.created_by, self.staff)

        listing = self.client.get(reverse("tenant-list"))
        self.assertEqual(listing.status_code, 200)
        self.assertIn(tenant, listing.context["tenants"])
        self.assertEqual(list(tenant.tenancies.all()), [])

    def test_tenancy_form_only_offers_visible_or_creator_owned_tenants(self):
        from django.urls import reverse

        own_unassigned = Tenant.objects.create(
            full_name="Owned Unassigned Tenant",
            created_by=self.staff,
        )
        self.client.force_login(self.staff)
        response = self.client.get(
            f"{reverse('tenancy-create')}?tenant={own_unassigned.pk}"
        )

        self.assertEqual(response.status_code, 200)
        choices = list(response.context["form"].fields["tenant"].queryset)
        self.assertIn(own_unassigned, choices)
        self.assertNotIn(self.other_tenant, choices)
        units = list(response.context["form"].fields["unit"].queryset)
        self.assertEqual(units, [self.allowed_unit])

    def test_staff_without_property_assignment_cannot_create_tenant(self):
        from django.contrib.auth import get_user_model
        from django.urls import reverse

        unassigned = get_user_model().objects.create_user(
            username="unassigned-staff",
            password="test-password",
        )
        self.client.force_login(unassigned)
        response = self.client.post(
            reverse("tenant-create"),
            {"full_name": "Should Not Be Created"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Tenant.objects.filter(full_name="Should Not Be Created").exists())
