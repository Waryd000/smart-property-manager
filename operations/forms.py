from django import forms

from core.access import visible_properties
from properties.models import Unit
from .models import Expense, MaintenanceRequest


class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ["property", "unit", "description", "priority", "estimated_cost"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = visible_properties(user)
        self.fields["property"].queryset = allowed
        self.fields["unit"].queryset = Unit.objects.filter(property__in=allowed)

    def clean(self):
        cleaned = super().clean()
        prop, unit = cleaned.get("property"), cleaned.get("unit")
        if unit and prop and unit.property_id != prop.pk:
            self.add_error("unit", "Select a unit belonging to the selected property.")
        return cleaned


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["property", "category", "description", "amount", "incurred_on"]
        widgets = {"incurred_on": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property"].queryset = visible_properties(user)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Expense amount must be greater than zero.")
        return amount
