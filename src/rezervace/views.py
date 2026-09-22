from datetime import date, time

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .forms import ReservationCreateForm
from .models import ParkingSpot, Reservation


def _parse_reservation_window(data):
    selected_date = data.get('date')
    selected_start = data.get('start_time')
    selected_end = data.get('end_time')

    if isinstance(selected_date, str):
        selected_date = date.fromisoformat(selected_date)
    if isinstance(selected_start, str):
        selected_start = time.fromisoformat(selected_start)
    if isinstance(selected_end, str):
        selected_end = time.fromisoformat(selected_end)

    return (
        selected_date or timezone.localdate(),
        selected_start or time(8, 0),
        selected_end or time(16, 0),
    )


def _get_overlapping_reservation(user, selected_date, selected_start, selected_end):
    return Reservation.objects.filter(
        user=user,
        date=selected_date,
        start_time__lt=selected_end,
        end_time__gt=selected_start,
    ).order_by('created_at').first()


def _build_reservation_grid_context(user, spot_queryset, selected_date, selected_start, selected_end, selected_spot_id=None):
    editing_reservation = _get_overlapping_reservation(user, selected_date, selected_start, selected_end)

    if selected_spot_id is None and editing_reservation:
        selected_spot_id = editing_reservation.spot_id

    occupied_spot_ids = set(
        Reservation.objects.filter(
            date=selected_date,
            start_time__lt=selected_end,
            end_time__gt=selected_start,
        ).values_list('spot_id', flat=True)
    )

    spot_groups = []
    for lot_id, lot_name, floor in spot_queryset.values_list('lot_id', 'lot__name', 'lot__floor').distinct().order_by('lot__name', 'lot__floor'):
        lot_spots = [spot for spot in spot_queryset if spot.lot_id == lot_id]
        for spot in lot_spots:
            spot.is_occupied = spot.id in occupied_spot_ids
        spot_groups.append({
            'lot_name': lot_name,
            'floor': floor,
            'spots': lot_spots,
        })

    return {
        'spot_groups': spot_groups,
        'selected_date': selected_date,
        'selected_start': selected_start,
        'selected_end': selected_end,
        'editing_reservation': editing_reservation,
        'selected_spot_id': int(selected_spot_id) if selected_spot_id and str(selected_spot_id).isdigit() else None,
    }

# Dekorátor zajistí, že nepřihlášeného uživatele to automaticky přesměruje na login
@login_required
def dashboard_view(request):
    reservations = (
        Reservation.objects.filter(user=request.user)
        .select_related('spot', 'spot__lot')
        .order_by('date', 'start_time')
    )

    context = {
        'rezervace': reservations,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def reservation_create_view(request):
    spot_queryset = ParkingSpot.objects.filter(is_active=True).select_related('lot').order_by('lot__name', 'number')

    existing_reservation = None
    selected_spot_id = request.POST.get('spot') if request.method == 'POST' else request.GET.get('spot')
    if request.method == 'POST':
        selected_date, selected_start, selected_end = _parse_reservation_window(request.POST)
        existing_reservation = _get_overlapping_reservation(request.user, selected_date, selected_start, selected_end)
        form = ReservationCreateForm(request.POST, instance=existing_reservation, spot_queryset=spot_queryset, user=request.user)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()
            return redirect('dashboard')
    else:
        selected_date, selected_start, selected_end = _parse_reservation_window(request.GET)
        existing_reservation = _get_overlapping_reservation(request.user, selected_date, selected_start, selected_end)
        if not selected_spot_id and existing_reservation:
            selected_spot_id = str(existing_reservation.spot_id)
        selected_spot = spot_queryset.filter(pk=selected_spot_id).first() if selected_spot_id else None
        initial_data = {
            'date': existing_reservation.date if existing_reservation else selected_date,
            'start_time': existing_reservation.start_time if existing_reservation else selected_start,
            'end_time': existing_reservation.end_time if existing_reservation else selected_end,
            'spot': existing_reservation.spot if existing_reservation else selected_spot,
        }
        form = ReservationCreateForm(initial=initial_data, instance=existing_reservation, spot_queryset=spot_queryset, user=request.user)

    context = {
        'form': form,
        **_build_reservation_grid_context(
            request.user,
            spot_queryset,
            selected_date,
            selected_start,
            selected_end,
            selected_spot_id,
        ),
    }
    return render(request, 'reservation_form.html', context)


@login_required
def reservation_grid_fragment_view(request):
    spot_queryset = ParkingSpot.objects.filter(is_active=True).select_related('lot').order_by('lot__name', 'number')
    selected_date, selected_start, selected_end = _parse_reservation_window(request.GET)
    selected_spot_id = request.GET.get('spot')
    context = _build_reservation_grid_context(
        request.user,
        spot_queryset,
        selected_date,
        selected_start,
        selected_end,
        selected_spot_id,
    )
    return render(request, 'reservation_grid.html', context)


@login_required
def reservation_delete_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id, user=request.user)
    if request.method == 'POST':
        reservation.delete()
    return redirect('dashboard')