from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import StaffProfile
from properties.models import Landlord, Property, PropertyAssignment, Unit


class PropertyMasterDataPermissionTests(TestCase):
    def setUp(self):
        self.landlord = Landlord.objects.create(full_name="Property Test Landlord")
        self.property = Property.objects.create(
            landlord=self.landlord,
            name="Assigned Property",
            address="Kampala",
        )
        self.staff = get_user_model().objects.create_user(
            username="unit-staff",
            password="test-password",
            is_staff=True,
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)
        PropertyAssignment.objects.create(property=self.property, staff=self.staff)

    def test_manager_can_open_add_unit_form(self):
        manager = get_user_model().objects.create_user(
            username="unit-manager",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(manager)
        response = self.client.get(reverse("unit-create"))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_open_add_unit_form_even_if_django_is_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("unit-create"))
        self.assertEqual(response.status_code, 302)

    def test_staff_cannot_create_unit_by_post(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("unit-create"),
            {
                "property": self.property.pk,
                "unit_number": "BLOCK-99",
                "monthly_rent": "180000.00",
                "status": "VACANT",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Unit.objects.filter(property=self.property, unit_number="BLOCK-99").exists())

    def test_property_list_hides_master_data_controls_from_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("property-list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("unit-create"))
        self.assertNotContains(response, reverse("property-create"))
