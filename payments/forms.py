from django import forms


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
