from django import forms
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm

from apps.cms.models import SiteSettings
from apps.users.models import User


class StaffPasswordChangeForm(DjangoPasswordChangeForm):
    """Password change with the panel's input styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "cx-input"


class GeneralSettingsForm(forms.ModelForm):
    """Editable business info — backed by the real SiteSettings singleton."""

    class Meta:
        model = SiteSettings
        fields = [
            "brand_name",
            "tagline",
            "phone",
            "address",
            "operating_hours",
            "whatsapp_number",
            "instagram_handle",
        ]
        widgets = {
            "brand_name": forms.TextInput(attrs={"class": "cx-input"}),
            "tagline": forms.TextInput(attrs={"class": "cx-input"}),
            "phone": forms.TextInput(attrs={"class": "cx-input"}),
            "address": forms.TextInput(attrs={"class": "cx-input"}),
            "operating_hours": forms.TextInput(attrs={"class": "cx-input"}),
            "whatsapp_number": forms.TextInput(attrs={"class": "cx-input"}),
            "instagram_handle": forms.TextInput(attrs={"class": "cx-input"}),
        }


class StaffProfileForm(forms.ModelForm):
    """Edit staff member's own profile details."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "cx-input"}),
            "last_name": forms.TextInput(attrs={"class": "cx-input"}),
            "phone": forms.TextInput(attrs={"class": "cx-input"}),
        }
