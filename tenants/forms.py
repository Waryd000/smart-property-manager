from django import forms
from django.core.exceptions import ValidationError

from .models import Tenant, Tenancy


AGREEMENT_MAX_SIZE = 5 * 1024 * 1024


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
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_agreement_file(self):
        uploaded = self.cleaned_data.get("agreement_file")
        if not uploaded or getattr(uploaded, "_committed", False):
            return uploaded
        if uploaded.size > AGREEMENT_MAX_SIZE:
            raise ValidationError("Agreement files must be 5 MB or smaller.")

        extension = uploaded.name.lower().rsplit(".", 1)[-1] if "." in uploaded.name else ""
        if extension not in {"pdf", "jpg", "jpeg", "png"}:
            raise ValidationError("Upload an agreement as PDF, JPG or PNG.")

        signature = uploaded.read(8)
        uploaded.seek(0)
        valid = (
            extension == "pdf" and signature.startswith(b"%PDF-")
        ) or (
            extension in {"jpg", "jpeg"} and signature.startswith(b"\xff\xd8\xff")
        ) or (
            extension == "png" and signature.startswith(b"\x89PNG\r\n\x1a\n")
        )
        if not valid:
            raise ValidationError(
                "The file contents do not match the selected PDF, JPG or PNG format."
            )
        return uploaded

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


class TenancyConfirmForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Enter the date the tenant actually took possession.",
    )


class TenancyEndForm(forms.Form):
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Enter the tenant's confirmed final occupancy date.",
    )
