from datetime import time

from django import forms
from django.utils import timezone

from .models import ParkingSpot, Reservation


class ReservationCreateForm(forms.ModelForm):
    date = forms.DateField(
        label='Datum',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    start_time = forms.TimeField(
        label='Od',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    end_time = forms.TimeField(
        label='Do',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    spot = forms.ModelChoiceField(
        label='Parkovací místo',
        queryset=ParkingSpot.objects.none(),
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Reservation
        fields = ['date', 'start_time', 'end_time', 'spot']

    def __init__(self, *args, **kwargs):
        spot_queryset = kwargs.pop('spot_queryset', ParkingSpot.objects.none())
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['spot'].queryset = spot_queryset

        self.fields['date'].initial = timezone.localdate()
        self.fields['start_time'].initial = time(8, 0)
        self.fields['end_time'].initial = time(16, 0)

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        spot = cleaned_data.get('spot')

        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'Čas „Do“ musí být později než „Od“.')
            return cleaned_data

        if spot and date and start_time and end_time:
            overlaps = Reservation.objects.filter(
                spot=spot,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if self.instance.pk:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                self.add_error('spot', 'Vybrané místo už je v tomto čase obsazené.')

        if self.user and date and start_time and end_time:
            user_overlaps = Reservation.objects.filter(
                user=self.user,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if self.instance.pk:
                user_overlaps = user_overlaps.exclude(pk=self.instance.pk)
            if user_overlaps.exists():
                self.add_error('date', 'V tomto čase už máte jinou rezervaci.')

        return cleaned_data