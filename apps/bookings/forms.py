from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.games.models import GameConsole
from apps.bookings.pricing import RATE_PER_PLAYER_HOUR


class BookingCreateForm(forms.Form):
    booking_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-input"}),
    )
    duration_hours = forms.IntegerField(
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": "1", "max": "10"}),
    )
    number_of_players = forms.IntegerField(
        min_value=1,
        max_value=4,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": "1", "max": "4"}),
    )
    game_console = forms.ModelChoiceField(
        queryset=GameConsole.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-input"}),
    )

    def clean_number_of_players(self):
        num = self.cleaned_data["number_of_players"]
        if num not in RATE_PER_PLAYER_HOUR:
            raise forms.ValidationError("Invalid number of players selected.")
        return num
