from django import forms

from tenants.models import Tenancy
from .models import Property, Unit


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ["name", "address", "description", "status", "landlord"]


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["property", "unit_number", "monthly_rent", "status", "notes"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        from core.access import visible_properties
        allowed = visible_properties(user)
        self.fields["property"].queryset = allowed

    def clean(self):
        cleaned = super().clean()
        unit = self.instance
        new_status = cleaned.get("status")
        if unit.pk and new_status in {"VACANT", "INACTIVE"}:
            has_live_tenancy = Tenancy.objects.filter(
                unit=unit,
                status__in=["ACTIVE", "PENDING"],
            ).exists()
            if has_live_tenancy:
                self.add_error(
                    "status",
                    "A unit with an active or pending tenancy cannot be marked vacant or inactive.",
                )
        return cleaned
