from django import forms

from core.access import visible_properties
from tenants.models import Tenant, Tenancy
from .models import Payment


MAX_BANK_CSV_SIZE = 5 * 1024 * 1024


class BankStatementImportForm(forms.Form):
    statement_file = forms.FileField(
        label="Incoming bank transactions CSV",
        help_text="Upload a UTF-8 CSV containing incoming credits only.",
    )

    def clean_statement_file(self):
        uploaded = self.cleaned_data["statement_file"]
        if not uploaded.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a .csv file, not an Excel workbook.")
        if uploaded.size > MAX_BANK_CSV_SIZE:
            raise forms.ValidationError("The CSV file must be 5 MB or smaller.")
        return uploaded


class PaymentRecordForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "tenant",
            "property",
            "amount",
            "bank_reference",
            "payment_date",
            "source_note",
        ]
        widgets = {
            "payment_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }
        help_texts = {
            "bank_reference": "Enter the exact reference from the bank statement.",
            "amount": "Enter the amount received in UGX.",
            "payment_date": "Optional date/time recorded by the bank.",
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        allowed_properties = visible_properties(user)
        self.fields["property"].queryset = allowed_properties
        self.fields["property"].required = True
        self.fields["tenant"].queryset = Tenant.objects.filter(
            tenancies__unit__property__in=allowed_properties
        ).distinct().order_by("full_name")

    def clean(self):
        cleaned = super().clean()
        tenant = cleaned.get("tenant")
        property_record = cleaned.get("property")
        if tenant and property_record and not Tenancy.objects.filter(
            tenant=tenant,
            unit__property=property_record,
        ).exists():
            self.add_error(
                "tenant",
                "This tenant has no tenancy in the selected property.",
            )
        return cleaned
