from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import (
    ActiveState,
    CancelledState,
    ExpiredState,
    ParkingLot,
    ParkingSpot,
    PendingState,
    Reservation,
)


class ReservationStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='employee', password='test-password')
        lot = ParkingLot.objects.create(name='Main lot', floor=0)
        self.spot = ParkingSpot.objects.create(lot=lot, number='A1')

    def create_reservation(self, state_code=Reservation.State.PENDING):
        return Reservation.objects.create(
            user=self.user,
            spot=self.spot,
            date=date.today(),
            start_time=time(8),
            end_time=time(16),
            state_code=state_code,
            locked_until=timezone.now() + timedelta(minutes=5),
        )

    def test_pending_reservation_can_be_confirmed(self):
        reservation = self.create_reservation()

        self.assertIsInstance(reservation.getState(), PendingState)
        self.assertTrue(reservation.confirm())
        reservation.refresh_from_db()
        self.assertIsInstance(reservation.getState(), ActiveState)

    def test_active_reservation_can_be_cancelled(self):
        reservation = self.create_reservation(Reservation.State.ACTIVE)

        self.assertTrue(reservation.cancel())
        reservation.refresh_from_db()
        self.assertIsInstance(reservation.getState(), CancelledState)

    def test_active_reservation_can_expire(self):
        reservation = self.create_reservation(Reservation.State.ACTIVE)

        self.assertTrue(reservation.expire())
        reservation.refresh_from_db()
        self.assertIsInstance(reservation.getState(), ExpiredState)

    def test_pending_reservation_cancel_deletes_reservation(self):
        reservation = self.create_reservation()

        self.assertTrue(reservation.cancel())
        self.assertFalse(Reservation.objects.filter(pk=reservation.pk).exists())

    def test_cancelled_state_rejects_transitions(self):
        reservation = self.create_reservation(Reservation.State.CANCELLED)

        self.assertFalse(reservation.confirm())
        self.assertFalse(reservation.cancel())
        self.assertFalse(reservation.expire())

    def test_expired_state_rejects_transitions(self):
        reservation = self.create_reservation(Reservation.State.EXPIRED)

        self.assertFalse(reservation.confirm())
        self.assertFalse(reservation.cancel())
        self.assertFalse(reservation.expire())


class ParkingAvailabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='employee', password='test-password')
        self.lot = ParkingLot.objects.create(name='Main lot', floor=0)
        self.spot = ParkingSpot.objects.create(lot=self.lot, number='A1')

    def test_overlapping_active_reservation_blocks_spot(self):
        Reservation.objects.create(
            user=self.user,
            spot=self.spot,
            date=date.today(),
            start_time=time(9),
            end_time=time(11),
            state_code=Reservation.State.ACTIVE,
        )

        self.assertFalse(self.spot.isAvailable(date.today(), time(10), time(12)))

    def test_cancelled_reservation_does_not_block_spot(self):
        Reservation.objects.create(
            user=self.user,
            spot=self.spot,
            date=date.today(),
            start_time=time(9),
            end_time=time(11),
            state_code=Reservation.State.CANCELLED,
        )

        self.assertTrue(self.spot.isAvailable(date.today(), time(10), time(12)))

    def test_pillar_and_empty_cells_are_not_reservable(self):
        pillar = ParkingSpot.objects.create(
            lot=self.lot,
            number='',
            cell_kind=ParkingSpot.CellKind.PILLAR,
            layout_row=2,
            layout_column=2,
        )
        empty = ParkingSpot.objects.create(
            lot=self.lot,
            number='',
            cell_kind=ParkingSpot.CellKind.EMPTY,
            layout_row=2,
            layout_column=3,
        )

        self.assertFalse(pillar.isAvailable(date.today(), time(8), time(16)))
        self.assertFalse(empty.isAvailable(date.today(), time(8), time(16)))


class ReservationExpirationTests(TestCase):
    def test_past_active_reservation_is_expired_from_dashboard(self):
        user = User.objects.create_user(
            username='expired-user',
            password='test-password',
        )
        lot = ParkingLot.objects.create(name='Lot', floor=0)
        spot = ParkingSpot.objects.create(lot=lot, number='E1')
        reservation = Reservation.objects.create(
            user=user,
            spot=spot,
            date=date.today() - timedelta(days=1),
            start_time=time(8),
            end_time=time(16),
            state_code=Reservation.State.ACTIVE,
        )

        self.client.login(username='expired-user', password='test-password')
        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.assertEqual(reservation.state_code, Reservation.State.EXPIRED)
        self.assertIsInstance(reservation.getState(), ExpiredState)


class ReservationLockTests(TestCase):
    def setUp(self):
        self.first_user = User.objects.create_user(
            username='first',
            email='first@example.com',
            password='test-password',
        )
        self.second_user = User.objects.create_user(
            username='second',
            email='second@example.com',
            password='test-password',
        )
        lot = ParkingLot.objects.create(name='Main lot', floor=0)
        self.spot = ParkingSpot.objects.create(lot=lot, number='A1')

    def lock_payload(self):
        return {
            'spot': self.spot.id,
            'date': date.today().isoformat(),
            'start_time': '08:00',
            'end_time': '16:00',
        }

    def test_first_user_lock_is_visible_to_second_user(self):
        self.client.login(username='first', password='test-password')
        lock_response = self.client.post('/reservations/lock/', self.lock_payload())
        self.assertEqual(lock_response.status_code, 200)

        self.client.login(username='second', password='test-password')
        fragment_response = self.client.get(
            '/reservations/new/grid/',
            {
                'date': date.today().isoformat(),
                'start_time': '08:00',
                'end_time': '16:00',
            },
        )
        self.assertContains(fragment_response, 'Vybráno jiným uživatelem')

    def test_second_user_cannot_take_currently_locked_spot(self):
        self.client.login(username='first', password='test-password')
        self.assertEqual(
            self.client.post('/reservations/lock/', self.lock_payload()).status_code,
            200,
        )

        self.client.login(username='second', password='test-password')
        response = self.client.post('/reservations/lock/', self.lock_payload())
        self.assertEqual(response.status_code, 409)

    def test_expired_pending_reservation_releases_spot(self):
        lock = Reservation.objects.create(
            user=self.first_user,
            spot=self.spot,
            date=date.today(),
            start_time=time(8),
            end_time=time(16),
            state_code=Reservation.State.PENDING,
            locked_until=timezone.now() - timedelta(minutes=1),
        )

        self.client.login(username='second', password='test-password')
        response = self.client.post('/reservations/lock/', self.lock_payload())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Reservation.objects.filter(pk=lock.pk).exists())


class AdministrationTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='test-password',
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='test-password',
            is_staff=True,
        )

    def test_employee_cannot_open_admin_dashboard(self):
        self.client.login(username='employee', password='test-password')

        response = self.client.get('/manage/')

        self.assertEqual(response.status_code, 302)

    def test_staff_can_open_admin_dashboard(self):
        self.client.login(username='admin', password='test-password')

        response = self.client.get('/manage/')

        self.assertEqual(response.status_code, 200)

    def test_admin_access_button_is_visible_for_staff(self):
        self.client.login(username='admin', password='test-password')

        response = self.client.get('/dashboard/')

        self.assertContains(response, 'Administrace')
        self.assertContains(response, '/manage/')

    def test_dashboard_contains_theme_and_password_controls(self):
        self.client.login(username='employee', password='test-password')

        response = self.client.get('/dashboard/')

        self.assertContains(response, 'id="themeToggle"')
        self.assertContains(response, 'parksys-theme')
        self.assertContains(response, 'Změnit heslo')

    def test_staff_can_create_employee(self):
        self.client.login(username='admin', password='test-password')

        response = self.client.post('/manage/users/add/', {
            'email': 'new.employee@example.com',
        })

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email='new.employee@example.com')
        self.assertEqual(user.username, 'new.employee@example.com')
        self.assertContains(response, 'Účet byl vytvořen')
        self.assertContains(response, 'new.employee@example.com')
        self.assertContains(response, 'Dočasné heslo:')
        self.assertTrue(user.parksys_profile.must_change_password)

    def test_new_employee_is_forced_to_change_password(self):
        user = User.objects.create_user(
            username='forced',
            email='forced@example.com',
            password='Temporary123!',
        )
        user.parksys_profile.must_change_password = True
        user.parksys_profile.save()
        self.client.login(username='forced', password='Temporary123!')

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/password/change/')

    def test_user_can_change_password(self):
        user = User.objects.create_user(
            username='changing',
            email='changing@example.com',
            password='Temporary123!',
        )
        self.client.login(username='changing', password='Temporary123!')

        response = self.client.post('/password/change/', {
            'old_password': 'Temporary123!',
            'new_password1': 'Permanent-Password-456!',
            'new_password2': 'Permanent-Password-456!',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')
        user.refresh_from_db()
        self.assertTrue(user.check_password('Permanent-Password-456!'))
        self.assertFalse(user.parksys_profile.must_change_password)

    def test_staff_can_create_lot_and_spots_with_layout(self):
        self.client.login(username='admin', password='test-password')

        lot_response = self.client.post('/manage/lots/add/', {
            'name': 'Nadzemní parkoviště',
            'floor': 1,
            'layout_rows': 3,
            'layout_columns': 5,
        })

        lot = ParkingLot.objects.get(name='Nadzemní parkoviště')
        spot_response = self.client.post(f'/manage/lots/{lot.id}/spots/add/', {
            'number': 'N01',
            'cell_kind': 'SPOT',
            'spot_type': 'NORMAL',
            'is_active': 'on',
            'layout_row': 2,
            'layout_column': 4,
        })

        self.assertEqual(lot_response.status_code, 302)
        self.assertEqual(spot_response.status_code, 302)
        spot = ParkingSpot.objects.get(lot=lot, number='N01')
        self.assertEqual((spot.layout_row, spot.layout_column), (2, 4))

    def test_staff_can_bulk_create_spots(self):
        self.client.login(username='admin', password='test-password')
        lot = ParkingLot.objects.create(
            name='Hromadné parkoviště',
            floor=0,
            layout_rows=4,
            layout_columns=5,
        )

        response = self.client.post(
            f'/manage/lots/{lot.id}/spots/bulk/',
            {
                'prefix': 'A',
                'start_number': 1,
                'count': 12,
                'spot_type': 'NORMAL',
                'is_active': 'on',
                'start_row': 1,
                'start_column': 1,
                'direction': 'ROW',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(lot.spots.count(), 12)
        self.assertTrue(lot.spots.filter(number='A01', layout_row=1, layout_column=1).exists())
        self.assertTrue(lot.spots.filter(number='A12', layout_row=3, layout_column=2).exists())
