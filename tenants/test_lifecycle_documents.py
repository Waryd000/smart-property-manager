import tempfile
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import StaffProfile
from operations.models import AuditLog
from properties.models import Landlord, Property, PropertyAssignment, Unit
from tenants.models import Tenant, Tenancy


class TenancyLifecycleAndDocumentTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)
        self.addCleanup(self.media_dir.cleanup)

        User = get_user_model()
        self.manager = User.objects.create_user(
            username="tenancy-manager", password="test-password", is_staff=True
        )
        self.staff = User.objects.create_user(
            username="tenancy-staff", password="test-password", is_staff=True
        )
        StaffProfile.objects.create(user=self.staff, role="STAFF", is_active=True)

        landlord = Landlord.objects.create(full_name="Tenancy Lifecycle Landlord")
        self.property = Property.objects.create(
            landlord=landlord, name="Lifecycle Property", address="Kampala"
        )
        self.other_property = Property.objects.create(
            landlord=landlord, name="Other Lifecycle Property", address="Kampala"
        )
        self.unit = Unit.objects.create(
            property=self.property, unit_number="LIFE-1",
            monthly_rent=Decimal("250000"), status="VACANT",
        )
        self.other_unit = Unit.objects.create(
            property=self.other_property, unit_number="LIFE-2",
            monthly_rent=Decimal("250000"), status="VACANT",
        )
        self.tenant = Tenant.objects.create(
            full_name="Lifecycle Tenant",
            created_by=self.staff,
        )
        PropertyAssignment.objects.create(property=self.property, staff=self.staff)

    def tenancy_data(self, **overrides):
        data = {
            "tenant": self.tenant.pk,
            "unit": self.unit.pk,
            "start_date": "2026-11-01",
            "monthly_rent": "250000.00",
            "deposit_amount": "0.00",
            "due_day": "5",
            "status": "PENDING",
        }
        data.update(overrides)
        return data

    def test_staff_cannot_create_an_active_tenancy_directly(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("tenancy-create"),
            self.tenancy_data(status="ACTIVE"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tenancy.objects.count(), 0)
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, "VACANT")

    def test_staff_can_create_pending_tenancy_but_unit_remains_vacant(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("tenancy-create"),
            self.tenancy_data(start_date=""),
        )

        self.assertEqual(response.status_code, 302)
        tenancy = Tenancy.objects.get()
        self.assertEqual(tenancy.status, "PENDING")
        self.assertIsNone(tenancy.start_date)
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, "VACANT")
        self.assertTrue(AuditLog.objects.filter(
            action="TENANCY_CREATED",
            record_id=str(tenancy.pk),
        ).exists())

    def test_manager_can_confirm_pending_tenancy_and_mark_unit_occupied(self):
        tenancy = Tenancy.objects.create(
            tenant=self.tenant,
            unit=self.unit,
            start_date=None,
            monthly_rent=Decimal("250000"),
            status="PENDING",
        )
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("tenancy-confirm", args=[tenancy.pk]),
            {"start_date": "2026-11-01"},
        )

        self.assertEqual(response.status_code, 302)
        tenancy.refresh_from_db()
        self.unit.refresh_from_db()
        self.assertEqual(tenancy.status, "ACTIVE")
        self.assertEqual(tenancy.start_date, date(2026, 11, 1))
        self.assertEqual(self.unit.status, "OCCUPIED")
        self.assertTrue(AuditLog.objects.filter(
            action="TENANCY_CONFIRMED",
            record_id=str(tenancy.pk),
        ).exists())

    def test_staff_cannot_confirm_pending_tenancy(self):
        tenancy = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=None,
            monthly_rent=Decimal("250000"), status="PENDING",
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("tenancy-confirm", args=[tenancy.pk]),
            {"start_date": "2026-11-01"},
        )

        tenancy.refresh_from_db()
        self.assertEqual(tenancy.status, "PENDING")

    def test_manager_cannot_confirm_unit_with_another_active_tenancy(self):
        another_tenant = Tenant.objects.create(full_name="Current Occupant")
        Tenancy.objects.create(
            tenant=another_tenant, unit=self.unit, start_date=date(2026, 1, 1),
            monthly_rent=Decimal("250000"), status="ACTIVE",
        )
        pending = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=None,
            monthly_rent=Decimal("250000"), status="PENDING",
        )
        self.client.force_login(self.manager)

        self.client.post(
            reverse("tenancy-confirm", args=[pending.pk]),
            {"start_date": "2026-11-01"},
        )

        pending.refresh_from_db()
        self.assertEqual(pending.status, "PENDING")

    def test_manager_ends_tenancy_and_marks_unit_vacant(self):
        tenancy = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=date(2026, 1, 1),
            monthly_rent=Decimal("250000"), status="ACTIVE",
        )
        self.unit.status = "OCCUPIED"
        self.unit.save(update_fields=["status"])
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("tenancy-end", args=[tenancy.pk]),
            {"end_date": "2026-11-15"},
        )

        self.assertEqual(response.status_code, 302)
        tenancy.refresh_from_db()
        self.unit.refresh_from_db()
        self.assertEqual(tenancy.status, "ENDED")
        self.assertEqual(tenancy.end_date, date(2026, 11, 15))
        self.assertEqual(self.unit.status, "VACANT")

    def test_staff_cannot_end_active_tenancy(self):
        tenancy = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=date(2026, 1, 1),
            monthly_rent=Decimal("250000"), status="ACTIVE",
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("tenancy-end", args=[tenancy.pk]),
            {"end_date": "2026-11-15"},
        )

        tenancy.refresh_from_db()
        self.assertEqual(tenancy.status, "ACTIVE")

    def test_valid_pdf_agreement_is_private_and_downloadable_by_assigned_staff(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("tenancy-create"),
            self.tenancy_data(
                agreement_file=SimpleUploadedFile(
                    "rental-agreement.pdf",
                    b"%PDF-1.4\nTest agreement content",
                    content_type="application/pdf",
                )
            ),
        )

        self.assertEqual(response.status_code, 302)
        tenancy = Tenancy.objects.get()
        self.assertTrue(tenancy.agreement_file.name.startswith("agreements/"))

        download = self.client.get(
            reverse("tenancy-agreement-download", args=[tenancy.pk])
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn("attachment", download["Content-Disposition"])
        self.assertEqual(
            b"".join(download.streaming_content),
            b"%PDF-1.4\nTest agreement content",
        )

    def test_html_disguised_as_pdf_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("tenancy-create"),
            self.tenancy_data(
                agreement_file=SimpleUploadedFile(
                    "fake-agreement.pdf",
                    b"<html><script>alert(1)</script></html>",
                    content_type="application/pdf",
                )
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tenancy.objects.count(), 0)
        self.assertContains(response, "contents do not match")

    def test_agreement_over_five_megabytes_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("tenancy-create"),
            self.tenancy_data(
                agreement_file=SimpleUploadedFile(
                    "large-agreement.pdf",
                    b"%PDF-1.4\n" + (b"x" * (5 * 1024 * 1024)),
                    content_type="application/pdf",
                )
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tenancy.objects.count(), 0)
        self.assertContains(response, "5 MB or smaller")

    def test_unassigned_staff_cannot_download_an_agreement(self):
        tenancy = Tenancy.objects.create(
            tenant=self.tenant, unit=self.unit, start_date=date(2026, 1, 1),
            monthly_rent=Decimal("250000"), status="ACTIVE",
            agreement_file=SimpleUploadedFile(
                "private.pdf", b"%PDF-1.4\nPrivate", content_type="application/pdf"
            ),
        )
        other_staff = get_user_model().objects.create_user(
            username="other-property-staff",
            password="test-password",
            is_staff=True,
        )
        StaffProfile.objects.create(user=other_staff, role="STAFF", is_active=True)
        self.client.force_login(other_staff)

        response = self.client.get(
            reverse("tenancy-agreement-download", args=[tenancy.pk])
        )

        self.assertEqual(response.status_code, 404)
