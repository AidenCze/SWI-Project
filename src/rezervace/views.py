from datetime import date, datetime, time, timedelta
import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Count, Q
import secrets
import string

from .forms import (
    EmployeeCreateForm,
    BulkParkingSpotForm,
    ParkingLotForm,
    ParkingSpotForm,
    ReservationCreateForm,
)
from .models import ParkingLot, ParkingSpot, Reservation


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


def _expire_due_reservations():
    now = timezone.now()
    Reservation.objects.filter(
        state_code=Reservation.State.PENDING,
        locked_until__lte=now,
    ).delete()

    active_reservations = Reservation.objects.filter(
        state_code=Reservation.State.ACTIVE,
    )
    for reservation in active_reservations:
        end_at = timezone.make_aware(
            datetime.combine(reservation.date, reservation.end_time),
            timezone.get_current_timezone(),
        )
        if end_at <= now:
            reservation.expire()


def _get_overlapping_reservation(user, selected_date, selected_start, selected_end):
    reservations = Reservation.objects.filter(
        user=user,
        date=selected_date,
        start_time__lt=selected_end,
        end_time__gt=selected_start,
    ).exclude(state_code__in=[Reservation.State.CANCELLED, Reservation.State.EXPIRED])
    now = timezone.now()
    return next(
        (
            reservation for reservation in reservations.order_by('created_at')
            if reservation.state_code != Reservation.State.PENDING
            or not reservation.locked_until
            or reservation.locked_until > now
        ),
        None,
    )


def _build_reservation_grid_context(user, spot_queryset, selected_date, selected_start, selected_end, selected_spot_id=None):
    editing_reservation = _get_overlapping_reservation(user, selected_date, selected_start, selected_end)

    if selected_spot_id is None and editing_reservation:
        selected_spot_id = editing_reservation.spot_id

    now = timezone.now()
    overlapping_reservations = Reservation.objects.filter(
        date=selected_date,
        start_time__lt=selected_end,
        end_time__gt=selected_start,
    ).exclude(state_code__in=[Reservation.State.CANCELLED, Reservation.State.EXPIRED])
    occupied_spot_ids = {
        reservation.spot_id
        for reservation in overlapping_reservations
        if reservation.state_code != Reservation.State.PENDING
        or not reservation.locked_until
        or reservation.locked_until > now
    }
    locked_by_other_spot_ids = {
        reservation.spot_id
        for reservation in overlapping_reservations
        if reservation.state_code == Reservation.State.PENDING
        and reservation.locked_until
        and reservation.locked_until > now
        and reservation.user_id != user.id
    }

    spot_groups = []
    for lot_id, lot_name, floor in spot_queryset.values_list('lot_id', 'lot__name', 'lot__floor').distinct().order_by('lot__name', 'lot__floor'):
        lot = ParkingLot.objects.get(pk=lot_id)
        lot_spots = [
            spot for spot in spot_queryset
            if spot.lot_id == lot_id
        ]
        lot_spots.sort(key=lambda spot: (spot.layout_row, spot.layout_column, spot.number))
        for spot in lot_spots:
            spot.is_occupied = spot.id in occupied_spot_ids
            spot.is_locked_by_other = spot.id in locked_by_other_spot_ids
        spot_groups.append({
            'lot_name': lot_name,
            'floor': floor,
            'layout_columns': lot.layout_columns,
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
    _expire_due_reservations()

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
    _expire_due_reservations()
    grid_queryset = ParkingSpot.objects.select_related('lot').order_by('lot__name', 'layout_row', 'layout_column')
    spot_queryset = grid_queryset.filter(
        is_active=True,
        cell_kind=ParkingSpot.CellKind.SPOT,
    )

    existing_reservation = None
    selected_spot_id = request.POST.get('spot') if request.method == 'POST' else request.GET.get('spot')
    if request.method == 'POST':
        selected_date, selected_start, selected_end = _parse_reservation_window(request.POST)
        existing_reservation = _get_overlapping_reservation(request.user, selected_date, selected_start, selected_end)
        form = ReservationCreateForm(request.POST, instance=existing_reservation, spot_queryset=spot_queryset, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    spot = ParkingSpot.objects.select_for_update().get(pk=form.cleaned_data['spot'].pk)
                    spot.confirmReservation(
                        form.cleaned_data['date'],
                        form.cleaned_data['start_time'],
                        form.cleaned_data['end_time'],
                        exclude_reservation_id=existing_reservation.pk if existing_reservation else None,
                    )
                    reservation = form.save(commit=False)
                    reservation.user = request.user
                    reservation.state_code = Reservation.State.PENDING
                    reservation.locked_until = timezone.now() + timedelta(minutes=5)
                    reservation.save()
                    reservation.confirm()
            except (ValueError, ParkingSpot.DoesNotExist):
                form.add_error('spot', 'Parkovací místo již rezervoval jiný uživatel.')
                selected_date, selected_start, selected_end = _parse_reservation_window(request.POST)
            else:
                messages.success(request, 'Rezervace byla vytvořena.')
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
            grid_queryset,
            selected_date,
            selected_start,
            selected_end,
            selected_spot_id,
        ),
    }
    return render(request, 'reservation_form.html', context)


@login_required
def reservation_grid_fragment_view(request):
    _expire_due_reservations()
    spot_queryset = ParkingSpot.objects.select_related('lot').order_by('lot__name', 'layout_row', 'layout_column')
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
def reservation_lock_view(request):
    if request.method != 'POST':
        return redirect('reservation_create')

    _expire_due_reservations()
    now = timezone.now()

    selected_spot_id = request.POST.get('spot')
    selected_date, selected_start, selected_end = _parse_reservation_window(request.POST)

    with transaction.atomic():
        Reservation.objects.filter(
            user=request.user,
            state_code=Reservation.State.PENDING,
        ).delete()

        if not selected_spot_id:
            return JsonResponse({'status': 'released'})

        spot = ParkingSpot.objects.select_for_update().filter(
            pk=selected_spot_id,
            is_active=True,
        ).first()
        if spot is None:
            return JsonResponse({'status': 'unavailable'}, status=409)

        overlap = Reservation.objects.select_for_update().filter(
            spot=spot,
            date=selected_date,
            start_time__lt=selected_end,
            end_time__gt=selected_start,
        ).exclude(state_code__in=[
            Reservation.State.CANCELLED,
            Reservation.State.EXPIRED,
        ])

        active_overlap = any(
            reservation.user_id != request.user.id
            and (
                reservation.state_code != Reservation.State.PENDING
                or not reservation.locked_until
                or reservation.locked_until > now
            )
            for reservation in overlap
        )
        if active_overlap:
            return JsonResponse({'status': 'occupied'}, status=409)
        own_active = overlap.filter(
            user=request.user,
            state_code=Reservation.State.ACTIVE,
        ).exists()
        if own_active:
            return JsonResponse({'status': 'owned'})

        lock = Reservation.objects.create(
            user=request.user,
            spot=spot,
            date=selected_date,
            start_time=selected_start,
            end_time=selected_end,
            state_code=Reservation.State.PENDING,
            locked_until=now + timedelta(minutes=5),
        )

    return JsonResponse({
        'status': 'locked',
        'reservation_id': lock.id,
        'locked_until': lock.locked_until.isoformat(),
    })


@login_required
def reservation_delete_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id, user=request.user)
    if request.method == 'POST':
        if reservation.cancel():
            messages.success(request, 'Rezervace byla zrušena.')
        else:
            messages.error(request, 'Rezervaci lze v tomto stavu zrušit.')
    return redirect('dashboard')


@staff_member_required
def admin_dashboard_view(request):
    today = timezone.localdate()
    active_reservations = Reservation.objects.filter(
        state_code=Reservation.State.ACTIVE,
        date__gte=today,
    )
    context = {
        'employee_count': User.objects.filter(is_active=True).count(),
        'parking_lot_count': ParkingSpot.objects.filter(is_active=True).count(),
        'active_reservation_count': active_reservations.count(),
        'today_reservation_count': active_reservations.filter(date=today).count(),
        'recent_reservations': (
            Reservation.objects.select_related('user', 'spot', 'spot__lot')
            .order_by('-created_at')[:8]
        ),
        'lots': (
            Reservation.objects.filter(date=today)
            .exclude(state_code__in=[Reservation.State.CANCELLED, Reservation.State.EXPIRED])
            .values('spot__lot__name')
            .annotate(total=Count('id'))
            .order_by('-total')
        ),
    }
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def admin_users_view(request):
    query = request.GET.get('q', '').strip()
    employees = User.objects.annotate(
        reservation_count=Count('reservations'),
    ).order_by('-is_staff', 'email', 'username')
    if query:
        employees = employees.filter(
            Q(email__icontains=query) | Q(username__icontains=query)
        )
    return render(request, 'admin/users.html', {
        'employees': employees,
        'query': query,
    })


@staff_member_required
def admin_user_create_view(request):
    created_credentials = None
    if request.method == 'POST':
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(14))
            User.objects.create_user(
                username=email,
                email=email,
                password=password,
            )
            created_credentials = {
                'email': email,
                'password': password,
                'text': (
                    'Vítejte v ParkSys.\n'
                    f'Přihlašovací e-mail: {email}\n'
                    f'Dočasné heslo: {password}'
                ),
            }
            form = EmployeeCreateForm()
    else:
        form = EmployeeCreateForm()
    return render(request, 'admin/user_create.html', {
        'form': form,
        'created_credentials': created_credentials,
    })


@staff_member_required
def admin_user_delete_view(request, user_id):
    employee = get_object_or_404(User, pk=user_id)
    if employee == request.user:
        messages.error(request, 'Nemůžete odebrat vlastní účet.')
        return redirect('admin_users')
    if request.method == 'POST':
        future_reservations = employee.reservations.filter(
            date__gte=timezone.localdate(),
            state_code__in=[Reservation.State.PENDING, Reservation.State.ACTIVE],
        )
        for reservation in future_reservations:
            reservation.cancel()
        employee.delete()
        messages.success(request, f'Uživatel {employee.username} byl odebrán.')
    return redirect('admin_users')


@staff_member_required
def admin_reservations_view(request):
    reservations = (
        Reservation.objects.select_related('user', 'spot', 'spot__lot')
        .order_by('-date', '-start_time')
    )
    query = request.GET.get('q', '').strip()
    date = request.GET.get('date', '').strip()
    state = request.GET.get('state', '').strip()
    spot = request.GET.get('spot', '').strip()

    if query:
        reservations = reservations.filter(
            Q(user__email__icontains=query)
            | Q(user__username__icontains=query)
            | Q(spot__number__icontains=query)
        )
    if date:
        reservations = reservations.filter(date=date)
    if state:
        reservations = reservations.filter(state_code=state)
    if spot:
        reservations = reservations.filter(spot__number__icontains=spot)

    return render(request, 'admin/reservations.html', {
        'reservations': reservations,
        'query': query,
        'date': date,
        'state': state,
        'spot': spot,
        'states': Reservation.State.choices,
    })


@staff_member_required
def admin_reservation_delete_view(request, reservation_id):
    reservation = get_object_or_404(
        Reservation.objects.select_related('user', 'spot'),
        pk=reservation_id,
    )
    if request.method == 'POST':
        if reservation.cancel():
            send_mail(
                subject='Rezervace parkovacího místa byla zrušena',
                message=(
                    f'Vaše rezervace místa {reservation.spot.number} '
                    f'dne {reservation.date} byla správcem zrušena.'
                ),
                from_email=None,
                recipient_list=[reservation.user.email] if reservation.user.email else [],
            )
            messages.success(request, 'Rezervace byla zrušena a uživatel informován.')
        else:
            messages.error(request, 'Rezervaci lze zrušit pouze v aktivním nebo čekajícím stavu.')
    return redirect('admin_reservations')


@staff_member_required
def admin_lots_view(request):
    lots = ParkingLot.objects.annotate(
        spot_count=Count('spots'),
        active_spot_count=Count('spots', filter=Q(spots__is_active=True)),
    ).order_by('name')
    return render(request, 'admin/lots.html', {'lots': lots})


@staff_member_required
def admin_lot_create_view(request):
    if request.method == 'POST':
        form = ParkingLotForm(request.POST)
        if form.is_valid():
            lot = form.save()
            messages.success(request, f'Parkoviště {lot.name} bylo vytvořeno.')
            return redirect('admin_lots')
    else:
        form = ParkingLotForm()
    return render(request, 'admin/lot_form.html', {
        'form': form,
        'title': 'Nové parkoviště',
    })


@staff_member_required
def admin_lot_edit_view(request, lot_id):
    lot = get_object_or_404(ParkingLot, pk=lot_id)
    if request.method == 'POST':
        form = ParkingLotForm(request.POST, instance=lot)
        if form.is_valid():
            form.save()
            messages.success(request, f'Parkoviště {lot.name} bylo upraveno.')
            return redirect('admin_lots')
    else:
        form = ParkingLotForm(instance=lot)
    return render(request, 'admin/lot_form.html', {
        'form': form,
        'lot': lot,
        'title': 'Upravit parkoviště',
    })


@staff_member_required
def admin_lot_delete_view(request, lot_id):
    lot = get_object_or_404(ParkingLot, pk=lot_id)
    if request.method == 'POST':
        lot_name = lot.name
        lot.delete()
        messages.success(request, f'Parkoviště {lot_name} bylo odstraněno.')
    return redirect('admin_lots')


@staff_member_required
def admin_spots_view(request, lot_id):
    lot = get_object_or_404(ParkingLot, pk=lot_id)
    spots = lot.spots.order_by('layout_row', 'layout_column', 'number')
    return render(request, 'admin/spots.html', {
        'lot': lot,
        'spots': spots,
    })


@staff_member_required
def admin_spot_create_view(request, lot_id):
    lot = get_object_or_404(ParkingLot, pk=lot_id)
    if request.method == 'POST':
        form = ParkingSpotForm(request.POST)
        form.fields.pop('lot')
        if form.is_valid():
            spot = form.save(commit=False)
            spot.lot = lot
            spot.save()
            messages.success(request, f'Místo {spot.number} bylo přidáno.')
            return redirect('admin_spots', lot_id=lot.id)
    else:
        form = ParkingSpotForm(initial={'lot': lot})
        form.fields.pop('lot')
    return render(request, 'admin/spot_form.html', {
        'form': form,
        'lot': lot,
        'title': 'Nové parkovací místo',
    })


@staff_member_required
def admin_spots_bulk_create_view(request, lot_id):
    lot = get_object_or_404(ParkingLot, pk=lot_id)
    if request.method == 'POST':
        form = BulkParkingSpotForm(request.POST)
        if form.is_valid():
            count = form.cleaned_data['count']
            start_number = form.cleaned_data['start_number']
            prefix = form.cleaned_data['prefix'].strip().upper()
            row = form.cleaned_data['start_row']
            column = form.cleaned_data['start_column']
            direction = form.cleaned_data['direction']
            number_width = max(2, len(str(start_number + count - 1)))

            spots_to_create = []
            occupied_numbers = set(
                lot.spots.values_list('number', flat=True)
            )
            occupied_positions = set(
                lot.spots.values_list('layout_row', 'layout_column')
            )

            for index in range(count):
                number = f"{prefix}{str(start_number + index).zfill(number_width)}"
                position = (row, column)

                if position[0] > lot.layout_rows or position[1] > lot.layout_columns:
                    form.add_error(None, 'Počet míst přesahuje rozměr a počet pozic parkoviště.')
                    break
                if number in occupied_numbers:
                    form.add_error('start_number', f'Místo {number} na tomto parkovišti již existuje.')
                    break
                if position in occupied_positions:
                    form.add_error('start_column', f'Pozice řada {row}, sloupec {column} je již obsazená.')
                    break

                spots_to_create.append(ParkingSpot(
                    lot=lot,
                    number=number,
                    spot_type=form.cleaned_data['spot_type'],
                    is_active=form.cleaned_data['is_active'],
                    layout_row=row,
                    layout_column=column,
                ))
                occupied_numbers.add(number)
                occupied_positions.add(position)

                if direction == 'ROW':
                    column += 1
                    if column > lot.layout_columns:
                        column = 1
                        row += 1
                else:
                    row += 1
                    if row > lot.layout_rows:
                        row = 1
                        column += 1

            if not form.errors:
                with transaction.atomic():
                    ParkingSpot.objects.bulk_create(spots_to_create)
                messages.success(request, f'Bylo vytvořeno {len(spots_to_create)} parkovacích míst.')
                return redirect('admin_spots', lot_id=lot.id)
    else:
        form = BulkParkingSpotForm()
    return render(request, 'admin/spots_bulk_create.html', {
        'form': form,
        'lot': lot,
    })


@staff_member_required
def admin_spot_edit_view(request, lot_id, spot_id):
    lot = get_object_or_404(ParkingLot, pk=lot_id)
    spot = get_object_or_404(ParkingSpot, pk=spot_id, lot=lot)
    if request.method == 'POST':
        form = ParkingSpotForm(request.POST, instance=spot)
        form.fields.pop('lot')
        if form.is_valid():
            updated_spot = form.save(commit=False)
            updated_spot.lot = lot
            updated_spot.save()
            messages.success(request, f'Místo {updated_spot.number} bylo upraveno.')
            return redirect('admin_spots', lot_id=lot.id)
    else:
        form = ParkingSpotForm(instance=spot)
        form.fields.pop('lot')
    return render(request, 'admin/spot_form.html', {
        'form': form,
        'lot': lot,
        'spot': spot,
        'title': 'Upravit parkovací místo',
    })


@staff_member_required
def admin_spot_delete_view(request, lot_id, spot_id):
    lot = get_object_or_404(ParkingLot, pk=lot_id)
    spot = get_object_or_404(ParkingSpot, pk=spot_id, lot=lot)
    if request.method == 'POST':
        spot.delete()
        messages.success(request, f'Místo {spot.number} bylo odstraněno.')
    return redirect('admin_spots', lot_id=lot.id)