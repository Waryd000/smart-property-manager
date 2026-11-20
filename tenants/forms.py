from django import forms

from .models import Tenant, Tenancy


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            "full_name",
            "phone",
            "email",
            "identification_reference",
            "emergency_contact",
            "notes",
        ]


class TenancyForm(forms.ModelForm):
    class Meta:
        model = Tenancy
        fields = [
            "tenant",
            "unit",
            "start_date",
            "end_date",
            "monthly_rent",
            "deposit_amount",
            "due_day",
            "status",
            "agreement_file",
        ]

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")

        if status == "ACTIVE" and not start_date:
            self.add_error(
                "start_date",
                "Confirm the tenancy start date before marking it active.",
            )
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "The end date cannot be before the start date.")
        return cleaned
