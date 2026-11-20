import json
import tempfile
from pathlib import Path

from django.core.management import call_command, CommandError
from django.test import TestCase

from properties.models import Landlord, Property, Unit
from tenants.models import Tenant, Tenancy


class NahaRegisterImportCommandTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.file_path = Path(self.tempdir.name) / "naha_register_import.json"

    def write_data(self, properties=None):
        data = {
            "source_file": "NAHA ASSETS 11234.xlsx",
            "landlord": {"full_name": "Waryd"},
            "properties": properties if properties is not None else [
                {
                    "name": "Bukesa",
                    "address": "Kampala",
                    "units": [
                        {
                            "unit_number": "A1",
                            "status": "OCCUPIED",
                            "monthly_rent": 450000,
                            "tenant": {"full_name": "Sample Tenant"},
                            "notes": "REVIEW: Check source row",
                        }
                    ],
                }
            ],
        }
        self.file_path.write_text(json.dumps(data), encoding="utf-8")
        return self.file_path

    def run_import(self, dry_run=False):
        call_command(
            "import_naha_register",
            file=str(self.file_path),
            dry_run=dry_run,
            verbosity=0,
        )

    def test_dry_run_checks_database_and_rolls_back_everything(self):
        self.write_data()

        self.run_import(dry_run=True)

        self.assertEqual(Landlord.objects.count(), 0)
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(Unit.objects.count(), 0)
        self.assertEqual(Tenant.objects.count(), 0)
        self.assertEqual(Tenancy.objects.count(), 0)

    def test_import_creates_names_pending_and_zero_rent(self):
        self.write_data()

        self.run_import()

        unit = Unit.objects.get(property__name="Bukesa", unit_number="A1")
        tenant = Tenant.objects.get(full_name="Sample Tenant")
        tenancy = Tenancy.objects.get(unit=unit, tenant=tenant)
        self.assertEqual(unit.monthly_rent, 0)
        self.assertEqual(unit.status, "PENDING_VERIFICATION")
        self.assertEqual(tenancy.monthly_rent, 0)
        self.assertEqual(tenancy.status, "PENDING")
        self.assertIsNone(tenancy.start_date)
        self.assertIn("NAHA ASSETS 11234.xlsx", unit.notes)
        self.assertIn("NAHA ASSETS 11234.xlsx", unit.property.description)

    def test_repeat_import_reuses_source_records_without_duplicates(self):
        self.write_data()

        self.run_import()
        self.run_import()

        self.assertEqual(Landlord.objects.count(), 1)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(Unit.objects.count(), 1)
        self.assertEqual(Tenant.objects.count(), 1)
        self.assertEqual(Tenancy.objects.count(), 1)

    def test_name_only_tenants_on_different_units_are_not_merged(self):
        self.write_data([
            {
                "name": "Bukesa",
                "units": [
                    {"unit_number": "A1", "tenant": {"full_name": "Alex Doe"}},
                    {"unit_number": "A2", "tenant": {"full_name": "Alex Doe"}},
                ],
            }
        ])

        self.run_import()

        self.assertEqual(Tenant.objects.filter(full_name="Alex Doe").count(), 2)
        self.assertEqual(Tenancy.objects.filter(status="PENDING").count(), 2)

    def test_existing_unmarked_property_causes_safe_abort_and_rollback(self):
        landlord = Landlord.objects.create(full_name="Waryd")
        Property.objects.create(
            landlord=landlord,
            name="Bukesa",
            address="Manual property",
        )
        self.write_data()

        with self.assertRaises(CommandError):
            self.run_import()

        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(Unit.objects.count(), 0)
        self.assertEqual(Tenant.objects.count(), 0)
        self.assertEqual(Tenancy.objects.count(), 0)

    def test_invalid_duplicate_unit_rows_are_rejected_before_database_write(self):
        self.write_data([
            {
                "name": "Bukesa",
                "units": [
                    {"unit_number": "A1"},
                    {"unit_number": " A1 "},
                ],
            }
        ])

        with self.assertRaises(CommandError):
            self.run_import()

        self.assertEqual(Landlord.objects.count(), 0)
