from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from properties.models import Property
from .models import StaffProfile


class StaffCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=30, required=False)
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES)
    password1 = forms.CharField(
        label="Temporary password",
        widget=forms.PasswordInput,
        strip=False,
    )
    password2 = forms.CharField(
        label="Confirm temporary password",
        widget=forms.PasswordInput,
        strip=False,
    )
    properties = forms.ModelMultipleChoiceField(
        queryset=Property.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["properties"].queryset = Property.objects.filter(
            status="ACTIVE"
        ).order_by("name")
        if not actor.is_superuser:
            self.fields["role"].choices = [("STAFF", "Staff")]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean(self):
        cleaned = super().clean()
        first, second = cleaned.get("password1"), cleaned.get("password2")
        if first and second and first != second:
            self.add_error("password2", "The two passwords do not match.")
        if first:
            candidate = User(
                username=cleaned.get("username", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
                email=cleaned.get("email", ""),
            )
            try:
                password_validation.validate_password(first, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        role = cleaned.get("role")
        if role == "MANAGER" and not self.actor.is_superuser:
            self.add_error("role", "Only a superuser can create another manager.")
        return cleaned


class StaffUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=30, required=False)
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES)
    is_active = forms.BooleanField(required=False)
    properties = forms.ModelMultipleChoiceField(
        queryset=Property.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, actor, profile, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.profile = profile
        self.fields["properties"].queryset = Property.objects.filter(
            status="ACTIVE"
        ).order_by("name")
        if not actor.is_superuser:
            self.fields["role"].choices = [("STAFF", "Staff")]
            self.fields["role"].disabled = True
        if profile.user.is_superuser and not actor.is_superuser:
            raise ValidationError("Only a superuser can administer a superuser account.")

    def clean_is_active(self):
        is_active = self.cleaned_data["is_active"]
        if self.profile.user_id == self.actor.pk and not is_active:
            raise forms.ValidationError("You cannot deactivate your own account.")
        return is_active

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role == "MANAGER" and not self.actor.is_superuser:
            raise forms.ValidationError("Only a superuser can assign the Manager role.")
        return role
