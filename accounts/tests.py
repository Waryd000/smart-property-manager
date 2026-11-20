from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import StaffProfile
from properties.models import Landlord, Property, PropertyAssignment


class StaffAdministrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(
            username="staff-admin-manager",
            password="test-password",
            is_staff=True,
        )
        self.staff = User.objects.create_user(
            username="existing-staff",
            password="test-password",
            is_staff=True,
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.staff,
            phone="0700000000",
            role="STAFF",
            is_active=True,
        )
        landlord = Landlord.objects.create(full_name="Staff Admin Landlord")
        self.property_one = Property.objects.create(
            landlord=landlord, name="Bukesa", address="Kampala"
        )
        self.property_two = Property.objects.create(
            landlord=landlord, name="Sir Apollo", address="Kampala"
        )
        self.list_url = reverse("staff-list")
        self.create_url = reverse("staff-create")

    def valid_create_data(self, **overrides):
        data = {
            "username": "new-property-staff",
            "first_name": "New",
            "last_name": "Officer",
            "email": "officer@example.com",
            "phone": "0712345678",
            "role": "STAFF",
            "password1": "V3ry-Long-C0mpl3x-P@ssphrase",
            "password2": "V3ry-Long-C0mpl3x-P@ssphrase",
            "properties": [str(self.property_one.pk)],
        }
        data.update(overrides)
        return data

    def test_non_manager_cannot_access_staff_administration(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.list_url).status_code, 302)
        self.assertEqual(self.client.get(self.create_url).status_code, 302)

    def test_manager_can_create_staff_account_and_property_assignment(self):
        self.client.force_login(self.manager)

        response = self.client.post(self.create_url, self.valid_create_data())

        self.assertRedirects(response, self.list_url)
        user = get_user_model().objects.get(username="new-property-staff")
        profile = user.staff_profile
        self.assertTrue(user.check_password("V3ry-Long-C0mpl3x-P@ssphrase"))
        self.assertTrue(user.is_staff)
        self.assertEqual(profile.role, "STAFF")
        self.assertTrue(profile.is_active)
        self.assertEqual(
            list(user.property_assignments.values_list("property_id", flat=True)),
            [self.property_one.pk],
        )

    def test_manager_cannot_create_another_manager(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            self.create_url,
            self.valid_create_data(role="MANAGER", username="attempted-manager"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username="attempted-manager").exists()
        )

    def test_superuser_can_create_manager_profile(self):
        superuser = get_user_model().objects.create_superuser(
            username="root-admin",
            email="root@example.com",
            password="test-password",
        )
        self.client.force_login(superuser)

        response = self.client.post(
            self.create_url,
            self.valid_create_data(role="MANAGER", username="new-manager"),
        )

        self.assertRedirects(response, self.list_url)
        profile = get_user_model().objects.get(username="new-manager").staff_profile
        self.assertEqual(profile.role, "MANAGER")

    def test_manager_can_update_staff_assignments_and_deactivate_account(self):
        PropertyAssignment.objects.create(
            property=self.property_one, staff=self.staff
        )
        self.client.force_login(self.manager)
        url = reverse("staff-update", args=[self.staff_profile.pk])

        response = self.client.post(
            url,
            {
                "first_name": "Edited",
                "last_name": "Officer",
                "email": "edited@example.com",
                "phone": "0799999999",
                "role": "STAFF",
                "is_active": "",
                "properties": [str(self.property_two.pk)],
            },
        )

        self.assertRedirects(response, self.list_url)
        self.staff.refresh_from_db()
        self.staff_profile.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Edited")
        self.assertFalse(self.staff.is_active)
        self.assertFalse(self.staff_profile.is_active)
        self.assertEqual(self.staff_profile.phone, "0799999999")
        self.assertEqual(
            list(self.staff.property_assignments.values_list("property_id", flat=True)),
            [self.property_two.pk],
        )

    def test_manager_cannot_deactivate_own_account(self):
        profile = StaffProfile.objects.create(
            user=self.manager, role="MANAGER", is_active=True
        )
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("staff-update", args=[profile.pk]),
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone": "",
                "role": "STAFF",
                "is_active": "",
                "properties": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.manager.refresh_from_db()
        self.assertTrue(self.manager.is_active)

    def test_manager_cannot_edit_superuser_staff_profile(self):
        superuser = get_user_model().objects.create_superuser(
            username="protected-superuser",
            email="protected@example.com",
            password="test-password",
        )
        profile = StaffProfile.objects.create(
            user=superuser, role="MANAGER", is_active=True
        )
        self.client.force_login(self.manager)

        response = self.client.get(reverse("staff-update", args=[profile.pk]))

        self.assertEqual(response.status_code, 404)
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_active)

    def test_duplicate_username_is_rejected(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            self.create_url,
            self.valid_create_data(username=self.staff.username),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.filter(username=self.staff.username).count(), 1)
