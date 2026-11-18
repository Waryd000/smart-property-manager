import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from properties.models import Landlord, Property, Unit
from tenants.models import Tenant, Tenancy


class Command(BaseCommand):
    help = (
        "Import the current property, unit and tenant registers from "
        "NAHA ASSETS 11234.xlsx. Historical payment columns are not posted."
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", default="import_data/naha_register_import.json")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        file_path = Path(options["file"]).expanduser()
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        if not file_path.exists():
            raise CommandError(
                f"Import file not found: {file_path}. "
                "Place naha_register_import.json in the import_data folder."
            )
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read import file: {exc}") from exc

        self._validate(data)
        properties = data["properties"]
        unit_count = sum(len(item["units"]) for item in properties)
        tenant_rows = sum(
            1 for item in properties for unit in item["units"] if unit.get("tenant")
        )
        review_count = sum(
            1 for item in properties for unit in item["units"]
            if "REVIEW:" in unit.get("notes", "")
        )
        self.stdout.write(self.style.NOTICE(
            f"Source: {data.get('source_file', 'unspecified')}"
        ))
        self.stdout.write(
            f"Landlord: {data['landlord']['full_name']} | "
            f"Properties: {len(properties)} | Units: {unit_count} | "
            f"Tenant register rows: {tenant_rows} | Review flags: {review_count}"
        )
        for item in properties:
            self.stdout.write(f"  {item['name']}: {len(item['units'])} units")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                "Dry run passed. No database records were changed."
            ))
            return

        created = {
            "landlords": 0, "properties": 0, "units": 0,
            "tenants": 0, "tenancies": 0,
        }
        reused = {"properties": 0, "units": 0, "tenants": 0, "tenancies": 0}

        with transaction.atomic():
            landlord_data = data["landlord"]
            landlord, landlord_created = Landlord.objects.get_or_create(
                full_name=landlord_data["full_name"],
                defaults={
                    "phone": landlord_data.get("phone", ""),
                    "email": landlord_data.get("email", ""),
                    "postal_address": landlord_data.get("postal_address", ""),
                    "notes": landlord_data.get("notes", ""),
                },
            )
            created["landlords"] += int(landlord_created)

            for property_data in properties:
                prop, property_created = Property.objects.get_or_create(
                    landlord=landlord,
                    name=property_data["name"],
                    defaults={
                        "address": property_data.get("address", "Address to be confirmed"),
                        "description": property_data.get("description", ""),
                        "status": "ACTIVE",
                    },
                )
                created["properties"] += int(property_created)
                reused["properties"] += int(not property_created)

                for unit_data in property_data["units"]:
                    unit, unit_created = Unit.objects.get_or_create(
                        property=prop,
                        unit_number=str(unit_data["unit_number"]),
                        defaults={
                            "monthly_rent": unit_data.get("monthly_rent", 0),
                            "status": unit_data.get("status", "PENDING_VERIFICATION"),
                            "notes": unit_data.get("notes", ""),
                        },
                    )
                    created["units"] += int(unit_created)
                    if not unit_created:
                        reused["units"] += 1
                        # Never overwrite records created or edited manually.
                        if "NAHA ASSETS 11234.xlsx" not in unit.notes:
                            raise CommandError(
                                f"{prop.name} unit {unit.unit_number} already exists "
                                "and is not marked as imported from the source workbook. "
                                "No import changes have been committed."
                            )

                    tenant_data = unit_data.get("tenant")
                    if not tenant_data:
                        continue

                    tenant, tenant_created = Tenant.objects.get_or_create(
                        full_name=tenant_data["full_name"],
                        phone=tenant_data.get("phone", ""),
                        notes=tenant_data.get("notes", ""),
                    )
                    created["tenants"] += int(tenant_created)
                    reused["tenants"] += int(not tenant_created)

                    _, tenancy_created = Tenancy.objects.get_or_create(
                        tenant=tenant,
                        unit=unit,
                        defaults={
                            "start_date": None,
                            "end_date": None,
                            "monthly_rent": unit_data.get("monthly_rent", 0),
                            "deposit_amount": 0,
                            "due_day": 5,
                            "status": unit_data.get("tenancy_status", "PENDING"),
                        },
                    )
                    created["tenancies"] += int(tenancy_created)
                    reused["tenancies"] += int(not tenancy_created)

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
        self.stdout.write(
            "Created: " + ", ".join(f"{key}={value}" for key, value in created.items())
        )
        self.stdout.write(
            "Reused: " + ", ".join(f"{key}={value}" for key, value in reused.items())
        )
        self.stdout.write(self.style.WARNING(
            "Historical payment figures were not posted as payments, rent charges, "
            "verified bank transactions or opening balances."
        ))

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict) or not isinstance(data.get("properties"), list):
            raise CommandError("Import file must contain a properties list.")
        landlord = data.get("landlord")
        if not isinstance(landlord, dict) or not landlord.get("full_name"):
            raise CommandError("A landlord full_name is required.")
        seen_properties = set()
        for prop in data["properties"]:
            if not prop.get("name") or prop["name"] in seen_properties:
                raise CommandError("Each property must have a unique, non-empty name.")
            seen_properties.add(prop["name"])
            seen_units = set()
            for unit in prop.get("units", []):
                unit_number = str(unit.get("unit_number", "")).strip()
                if not unit_number or unit_number in seen_units:
                    raise CommandError(
                        f"{prop['name']} contains an empty or duplicate unit number."
                    )
                seen_units.add(unit_number)
                if unit.get("status") not in {
                    "VACANT", "OCCUPIED", "MAINTENANCE", "INACTIVE",
                    "PENDING_VERIFICATION",
                }:
                    raise CommandError(
                        f"Unsupported unit status for {prop['name']} / {unit_number}."
                    )
                if unit.get("tenant") and not unit["tenant"].get("full_name"):
                    raise CommandError(
                        f"Tenant name missing for {prop['name']} / {unit_number}."
                    )
