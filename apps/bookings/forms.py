from django import forms
from django.utils import timezone
from .models import Booking
from apps.games.models import GameConsole

TIME_SLOTS = [
    ('10:00', '10:00 AM'),
    ('11:00', '11:00 AM'),
    ('12:00', '12:00 PM'),
    ('13:00', '01:00 PM'),
    ('14:00', '02:00 PM'),
    ('15:00', '03:00 PM'),
    ('16:00', '04:00 PM'),
    ('17:00', '05:00 PM'),
    ('18:00', '06:00 PM'),
    ('19:00', '07:00 PM'),
    ('20:00', '08:00 PM'),
    ('21:00', '09:00 PM'),
]

PLAYER_CHOICES = [(i, f'{i} Player{"s" if i > 1 else ""}') for i in range(1, 5)]

class BookingForm(forms.Form):
    console   = forms.ModelChoiceField(queryset=GameConsole.objects.filter(is_active=True), empty_label='Select a PS5 Setup')
    date      = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.ChoiceField(choices=TIME_SLOTS, label='Start Time')
    duration  = forms.ChoiceField(choices=[(1,'1 Hour'),(2,'2 Hours'),(3,'3 Hours'),(4,'4 Hours')], label='Duration')
    number_of_players = forms.ChoiceField(choices=PLAYER_CHOICES, label='Players')

    def clean_date(self):
        date = self.cleaned_data['date']
        if date < timezone.now().date():
            raise forms.ValidationError('Please select a future date.')
        return date

    def clean(self):
        cleaned = super().clean()
        console    = cleaned.get('console')
        date       = cleaned.get('date')
        start_time = cleaned.get('start_time')
        duration   = int(cleaned.get('duration', 1))

        if console and date and start_time:
            from datetime import time, timedelta, datetime
            h, m = map(int, start_time.split(':'))
            start = time(h, m)
            end_dt = datetime.combine(date, start) + timedelta(hours=duration)
            end = end_dt.time()
            cleaned['end_time'] = end

            # Check slot conflict
            conflict = Booking.objects.filter(
                console=console,
                date=date,
                status__in=['pending', 'confirmed', 'active'],
                start_time__lt=end,
                end_time__gt=start,
            ).exists()
            if conflict:
                raise forms.ValidationError('This slot is already booked. Please choose a different time or setup.')

        return cleaned
