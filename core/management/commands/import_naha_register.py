import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction

from properties.models import Landlord, Property, Unit
from tenants.models import Tenant, Tenancy


SOURCE_MARKER = "NAHA ASSETS 11234.xlsx"
IMPORT_FILE_LIMIT = 10 * 1024 * 1024


class Command(BaseCommand):
    help = (
        "Import reviewed property, unit and tenant names from a normalized "
        "NAHA register JSON file. Rent, payments and utilities are not imported."
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", default="import_data/naha_register_import.json")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Execute validation against the database and roll back all changes.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"]).expanduser()
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        if not file_path.exists():
            raise CommandError(
                f"Import file not found: {file_path}. "
                "Place naha_register_import.json in the import_data folder."
            )
        if file_path.stat().st_size > IMPORT_FILE_LIMIT:
            raise CommandError("The import JSON file must be 10 MB or smaller.")

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
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
            f"Source: {data.get('source_file', SOURCE_MARKER)}"
        ))
        self.stdout.write(
            f"Landlord: {data['landlord']['full_name']} | "
            f"Properties: {len(properties)} | Units: {unit_count} | "
            f"Tenant register rows: {tenant_rows} | Review flags: {review_count}"
        )

        created = {
            "landlords": 0,
            "properties": 0,
            "units": 0,
            "tenants": 0,
            "tenancies": 0,
        }
        reused = {
            "properties": 0,
            "units": 0,
            "tenants": 0,
            "tenancies": 0,
        }

        # Dry run executes the same lookups, uniqueness checks and writes as a
        # real import, but rolls the complete transaction back before returning.
        with transaction.atomic():
            landlord_data = data["landlord"]
            try:
                landlord, landlord_created = Landlord.objects.get_or_create(
                    full_name=landlord_data["full_name"],
                    defaults={
                        "phone": landlord_data.get("phone", ""),
                        "email": landlord_data.get("email", ""),
                        "postal_address": landlord_data.get("postal_address", ""),
                        "notes": landlord_data.get("notes", ""),
                    },
                )
            except MultipleObjectsReturned as exc:
                raise CommandError(
                    "More than one landlord has the imported name. "
                    "Resolve the duplicate landlord records before importing."
                ) from exc
            created["landlords"] += int(landlord_created)

            for property_data in properties:
                property_name = property_data["name"]
                source_description = self._with_source_marker(
                    property_data.get("description", "")
                )
                try:
                    prop, property_created = Property.objects.get_or_create(
                        landlord=landlord,
                        name=property_name,
                        defaults={
                            "address": property_data.get(
                                "address", "Address to be confirmed"
                            ),
                            "description": source_description,
                            "status": "ACTIVE",
                        },
                    )
                except MultipleObjectsReturned as exc:
                    raise CommandError(
                        f"{property_name} has duplicate records for this landlord. "
                        "Resolve them before importing."
                    ) from exc

                created["properties"] += int(property_created)
                reused["properties"] += int(not property_created)
                if not property_created and SOURCE_MARKER not in prop.description:
                    raise CommandError(
                        f"Property {property_name} already exists but is not marked "
                        "as imported from the NAHA register. Review it manually; "
                        "no import changes have been committed."
                    )

                for unit_data in property_data["units"]:
                    unit_number = str(unit_data["unit_number"]).strip()
                    tenant_data = unit_data.get("tenant")
                    imported_status = unit_data.get("status", "PENDING_VERIFICATION")
                    if tenant_data or imported_status == "OCCUPIED":
                        imported_status = "PENDING_VERIFICATION"

                    source_notes = self._with_source_marker(
                        unit_data.get("notes", "")
                    )
                    unit, unit_created = Unit.objects.get_or_create(
                        property=prop,
                        unit_number=unit_number,
                        defaults={
                            # User explicitly wants to review and enter rent later.
                            "monthly_rent": 0,
                            "status": imported_status,
                            "notes": source_notes,
                        },
                    )
                    created["units"] += int(unit_created)
                    reused["units"] += int(not unit_created)
                    if not unit_created and SOURCE_MARKER not in unit.notes:
                        raise CommandError(
                            f"{prop.name} unit {unit.unit_number} already exists "
                            "and is not marked as imported from the source workbook. "
                            "Review it manually; no import changes have been committed."
                        )

                    if not tenant_data:
                        continue

                    tenant = self._resolve_tenant(
                        unit=unit,
                        tenant_data=tenant_data,
                    )
                    tenant_created = getattr(tenant, "_import_created", False)
                    created["tenants"] += int(tenant_created)
                    reused["tenants"] += int(not tenant_created)

                    competing_tenancy = Tenancy.objects.filter(
                        unit=unit,
                        status__in=["ACTIVE", "PENDING"],
                    ).exclude(tenant=tenant).exists()
                    if competing_tenancy:
                        raise CommandError(
                            f"{prop.name} unit {unit.unit_number} already has another "
                            "active or pending tenant. Resolve the occupancy before "
                            "importing this row."
                        )

                    _, tenancy_created = Tenancy.objects.get_or_create(
                        tenant=tenant,
                        unit=unit,
                        defaults={
                            "start_date": None,
                            "end_date": None,
                            "monthly_rent": 0,
                            "deposit_amount": 0,
                            "due_day": 5,
                            "status": "PENDING",
                        },
                    )
                    created["tenancies"] += int(tenancy_created)
                    reused["tenancies"] += int(not tenancy_created)

            if options["dry_run"]:
                transaction.set_rollback(True)

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                "Dry run passed against the database. All changes were rolled back."
            ))
            self.stdout.write(
                "Would create: "
                + ", ".join(f"{key}={value}" for key, value in created.items())
            )
            self.stdout.write(
                "Would reuse: "
                + ", ".join(f"{key}={value}" for key, value in reused.items())
            )
            return

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))
        self.stdout.write(
            "Created: " + ", ".join(f"{key}={value}" for key, value in created.items())
        )
        self.stdout.write(
            "Reused: " + ", ".join(f"{key}={value}" for key, value in reused.items())
        )
        self.stdout.write(self.style.WARNING(
            "Monthly rent values were set to zero for manager review. Historical "
            "payments, utilities, rent charges and opening balances were not imported."
        ))

    @staticmethod
    def _with_source_marker(notes):
        notes = str(notes or "").strip()
        if SOURCE_MARKER in notes:
            return notes
        return f"Source: {SOURCE_MARKER}" + (f"\n{notes}" if notes else "")

    @staticmethod
    def _resolve_tenant(*, unit, tenant_data):
        full_name = " ".join(str(tenant_data.get("full_name", "")).split())
        phone = str(tenant_data.get("phone", "") or "").strip()
        email = str(tenant_data.get("email", "") or "").strip()
        if not full_name:
            raise CommandError(
                f"{unit.property.name} unit {unit.unit_number} has no tenant name."
            )

        # A phone and name together are used as a cross-property identity key.
        # Without a phone, only reuse the tenant already linked to this exact
        # imported unit. Name-only matching across units risks merging people
        # who happen to share a name.
        if phone:
            matches = Tenant.objects.filter(
                full_name__iexact=full_name,
                phone=phone,
            ).distinct()
        else:
            matches = Tenant.objects.filter(
                full_name__iexact=full_name,
                phone="",
                tenancies__unit=unit,
            ).distinct()

        match_count = matches.count()
        if match_count > 1:
            raise CommandError(
                f"More than one tenant matches {full_name!r} for "
                f"{unit.property.name} unit {unit.unit_number}. Resolve duplicates first."
            )
        if match_count == 1:
            return matches.first()

        tenant = Tenant.objects.create(
            full_name=full_name,
            phone=phone,
            email=email,
            notes=str(tenant_data.get("notes", "") or "").strip(),
        )
        tenant._import_created = True
        return tenant

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict) or not isinstance(data.get("properties"), list):
            raise CommandError("Import file must contain a properties list.")
        if not data["properties"]:
            raise CommandError("Import file contains no properties.")

        landlord = data.get("landlord")
        if not isinstance(landlord, dict) or not str(landlord.get("full_name", "")).strip():
            raise CommandError("A landlord full_name is required.")

        seen_properties = set()
        allowed_statuses = {
            "VACANT",
            "OCCUPIED",
            "MAINTENANCE",
            "INACTIVE",
            "PENDING_VERIFICATION",
        }
        for prop in data["properties"]:
            if not isinstance(prop, dict):
                raise CommandError("Each property entry must be an object.")
            name = " ".join(str(prop.get("name", "")).split())
            if not name or name in seen_properties:
                raise CommandError("Each property must have a unique, non-empty name.")
            prop["name"] = name
            seen_properties.add(name)

            units = prop.get("units")
            if not isinstance(units, list):
                raise CommandError(f"{name} must contain a units list.")
            seen_units = set()
            for unit in units:
                if not isinstance(unit, dict):
                    raise CommandError(f"{name} has an invalid unit row.")
                unit_number = str(unit.get("unit_number", "")).strip()
                if not unit_number or unit_number in seen_units:
                    raise CommandError(
                        f"{name} contains an empty or duplicate unit number."
                    )
                unit["unit_number"] = unit_number
                seen_units.add(unit_number)
                status = unit.get("status", "PENDING_VERIFICATION")
                if status not in allowed_statuses:
                    raise CommandError(
                        f"Unsupported unit status for {name} / {unit_number}."
                    )
                unit["status"] = status
                tenant = unit.get("tenant")
                if tenant is not None:
                    if not isinstance(tenant, dict) or not str(
                        tenant.get("full_name", "")
                    ).strip():
                        raise CommandError(
                            f"Tenant name missing for {name} / {unit_number}."
                        )
                    tenant["full_name"] = " ".join(
                        str(tenant["full_name"]).split()
                    )
