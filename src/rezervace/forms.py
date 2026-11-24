from datetime import time

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import ParkingLot, ParkingSpot, Reservation


class ParkingLotForm(forms.ModelForm):
    class Meta:
        model = ParkingLot
        fields = ['name', 'floor', 'layout_rows', 'layout_columns']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Například Severní parkoviště'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control', 'min': '-3', 'max': '50'}),
            'layout_rows': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '20'}),
            'layout_columns': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '12'}),
        }


class ParkingSpotForm(forms.ModelForm):
    class Meta:
        model = ParkingSpot
        fields = ['lot', 'number', 'cell_kind', 'spot_type', 'is_active', 'layout_row', 'layout_column']
        widgets = {
            'lot': forms.Select(attrs={'class': 'form-select'}),
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A01'}),
            'cell_kind': forms.Select(attrs={'class': 'form-select'}),
            'spot_type': forms.Select(attrs={'class': 'form-select'}),
            'layout_row': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'layout_column': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def clean(self):
        cleaned = super().clean()
        cell_kind = cleaned.get('cell_kind')
        number = (cleaned.get('number') or '').strip().upper()
        if cell_kind == ParkingSpot.CellKind.SPOT and not number:
            self.add_error('number', 'Parkovací místo musí mít číslo.')
        elif cell_kind != ParkingSpot.CellKind.SPOT:
            cleaned['number'] = ''
        if number and cell_kind == ParkingSpot.CellKind.SPOT:
            lot = cleaned.get('lot')
            duplicates = ParkingSpot.objects.filter(lot=lot, number__iexact=number)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error('number', 'Toto číslo místa už na parkovišti existuje.')
        cleaned['number'] = number if cell_kind == ParkingSpot.CellKind.SPOT else ''
        return cleaned


class BulkParkingSpotForm(forms.Form):
    prefix = forms.CharField(
        max_length=10,
        initial='A',
        label='Předpona',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A'}),
    )
    start_number = forms.IntegerField(
        min_value=1,
        initial=1,
        label='První číslo',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    count = forms.IntegerField(
        min_value=1,
        max_value=500,
        initial=20,
        label='Počet míst',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    spot_type = forms.ChoiceField(
        choices=ParkingSpot.SpotType.choices,
        initial=ParkingSpot.SpotType.NORMAL,
        label='Typ míst',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label='Místa jsou aktivní',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    start_row = forms.IntegerField(
        min_value=1,
        initial=1,
        label='Začít v řadě',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    start_column = forms.IntegerField(
        min_value=1,
        initial=1,
        label='Začít ve sloupci',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    direction = forms.ChoiceField(
        choices=(('ROW', 'Postupně po řádcích'), ('COLUMN', 'Postupně po sloupcích')),
        initial='ROW',
        label='Směr zaplnění',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class EmployeeCreateForm(forms.ModelForm):
    email = forms.EmailField(
        label='Firemní e-mail',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'jmeno@firma.cz'}),
    )

    class Meta:
        model = User
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Uživatel s tímto e-mailem již existuje.')
        return email


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
            ).exclude(state_code__in=[Reservation.State.CANCELLED, Reservation.State.EXPIRED])
            if self.instance.pk:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            now = timezone.now()
            active_overlap = any(
                (not self.user or reservation.user_id != self.user.id)
                and (
                    reservation.state_code != Reservation.State.PENDING
                    or not reservation.locked_until
                    or reservation.locked_until > now
                )
                for reservation in overlaps
            )
            if active_overlap:
                self.add_error('spot', 'Vybrané místo už je v tomto čase obsazené.')

        if self.user and date and start_time and end_time:
            user_overlaps = Reservation.objects.filter(
                user=self.user,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exclude(state_code__in=[Reservation.State.CANCELLED, Reservation.State.EXPIRED])
            if self.instance.pk:
                user_overlaps = user_overlaps.exclude(pk=self.instance.pk)
            now = timezone.now()
            active_user_overlap = any(
                reservation.state_code != Reservation.State.PENDING
                or not reservation.locked_until
                or reservation.locked_until > now
                for reservation in user_overlaps
            )
            if active_user_overlap:
                self.add_error('date', 'V tomto čase už máte jinou rezervaci.')

        return cleaned_data