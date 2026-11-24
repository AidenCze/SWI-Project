from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parksys_profile',
    )
    must_change_password = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Profil uživatele'
        verbose_name_plural = 'Profily uživatelů'

    def __str__(self):
        return f'Profil {self.user.username}'


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class ReservationState:
    """Base state for a reservation in the State design pattern."""

    def __init__(self, context):
        self.context = context

    def confirm(self):
        return False

    def cancel(self):
        return False

    def expire(self):
        return False


class PendingState(ReservationState):
    def confirm(self):
        self.context.setState(ActiveState(self.context))
        return True

    def cancel(self):
        self.context.delete()
        return True


class ActiveState(ReservationState):
    def cancel(self):
        self.context.setState(CancelledState(self.context))
        return True

    def expire(self):
        self.context.setState(ExpiredState(self.context))
        return True


class CancelledState(ReservationState):
    pass


class ExpiredState(ReservationState):
    pass

class ParkingLot(models.Model):
    name = models.CharField(max_length=100, verbose_name="Název parkoviště")
    floor = models.IntegerField(default=0, verbose_name="Patro")
    layout_columns = models.PositiveSmallIntegerField(default=4, verbose_name="Počet sloupců")
    layout_rows = models.PositiveSmallIntegerField(default=2, verbose_name="Počet řad")

    class Meta:
        verbose_name = "Parkoviště"
        verbose_name_plural = "Parkoviště"

    def __str__(self):
        return f"{self.name} (Patro {self.floor})"

    def getAvailableSpots(self, date, start_time, end_time):
        spots = self.spots.filter(is_active=True).prefetch_related('reservations')
        return [spot for spot in spots if spot.isAvailable(date, start_time, end_time)]


class ParkingSpot(models.Model):
    class SpotType(models.TextChoices):
        NORMAL = 'NORMAL', 'Běžné'
        DISABLED = 'DISABLED_ONLY', 'Vyhrazeno pro ZTP'
        EV = 'EV_ONLY', 'Nabíjecí stanice (EV)'

    class CellKind(models.TextChoices):
        SPOT = 'SPOT', 'Parkovací místo'
        EMPTY = 'EMPTY', 'Prázdná buňka'
        PILLAR = 'PILLAR', 'Pilíř / překážka'

    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='spots', verbose_name="Parkoviště")
    number = models.CharField(max_length=10, blank=True, verbose_name="Číslo místa")
    spot_type = models.CharField(max_length=20, choices=SpotType.choices, default=SpotType.NORMAL, verbose_name="Typ místa")
    is_active = models.BooleanField(default=True, verbose_name="Aktivní pro rezervace")
    layout_row = models.PositiveSmallIntegerField(default=1, verbose_name="Řada")
    layout_column = models.PositiveSmallIntegerField(default=1, verbose_name="Sloupec")
    cell_kind = models.CharField(
        max_length=10,
        choices=CellKind.choices,
        default=CellKind.SPOT,
        verbose_name="Typ buňky",
    )

    class Meta:
        verbose_name = "Parkovací místo"
        verbose_name_plural = "Parkovací místa"
        constraints = [
            models.UniqueConstraint(
                fields=['lot', 'layout_row', 'layout_column'],
                name='unique_parking_cell_position',
            ),
            models.UniqueConstraint(
                fields=['lot', 'number'],
                condition=~models.Q(number='') & ~models.Q(cell_kind__in=['EMPTY', 'PILLAR']),
                name='unique_reservable_spot_number',
            ),
        ]

    def __str__(self):
        return f"{self.number} ({self.get_spot_type_display()})"

    def isAvailable(self, date, start_time, end_time, exclude_reservation_id=None):
        if self.cell_kind != self.CellKind.SPOT or not self.is_active:
            return False
        now = timezone.now()
        overlapping = self.reservations.filter(
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exclude(state_code__in=['CANCELLED', 'EXPIRED'])
        if exclude_reservation_id:
            overlapping = overlapping.exclude(pk=exclude_reservation_id)

        for reservation in overlapping:
            if reservation.state_code != 'PENDING' or not reservation.locked_until or reservation.locked_until > now:
                return False
        return True

    def confirmReservation(self, date, start_time, end_time, exclude_reservation_id=None):
        if not self.isAvailable(date, start_time, end_time, exclude_reservation_id):
            raise ValueError("Parkovací místo není v tomto termínu dostupné.")

    def freeSpot(self, date, start_time, end_time):
        self.reservations.filter(
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
            state_code__in=['PENDING', 'ACTIVE'],
        ).update(state_code='CANCELLED')


class Reservation(models.Model):
    class State(models.TextChoices):
        PENDING = 'PENDING', 'Čeká na potvrzení'
        ACTIVE = 'ACTIVE', 'Aktivní'
        CANCELLED = 'CANCELLED', 'Zrušená'
        EXPIRED = 'EXPIRED', 'Vypršelá'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', verbose_name="Zaměstnanec")
    spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, related_name='reservations', verbose_name="Parkovací místo")
    
    date = models.DateField(verbose_name="Datum rezervace")
    start_time = models.TimeField(verbose_name="Od")
    end_time = models.TimeField(verbose_name="Do")
    state_code = models.CharField(
        max_length=10,
        choices=State.choices,
        default=State.ACTIVE,
        verbose_name="Stav",
    )
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name="Zámek platný do")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rezervace"
        verbose_name_plural = "Rezervace"

    def __str__(self):
        return f"{self.user.username} - {self.spot.number} ({self.date})"

    @property
    def state(self):
        return self.getState()

    def getState(self):
        state_types = {
            self.State.PENDING: PendingState,
            self.State.ACTIVE: ActiveState,
            self.State.CANCELLED: CancelledState,
            self.State.EXPIRED: ExpiredState,
        }
        return state_types[self.state_code](self)

    def setState(self, state):
        if not isinstance(state, ReservationState):
            raise ValueError("Neplatný typ stavu rezervace.")
        state_codes = {
            PendingState: self.State.PENDING,
            ActiveState: self.State.ACTIVE,
            CancelledState: self.State.CANCELLED,
            ExpiredState: self.State.EXPIRED,
        }
        state_code = state_codes[type(state)]
        self.state_code = state_code
        self.locked_until = None
        self.save(update_fields=['state_code', 'locked_until'])

    def confirm(self):
        return self.getState().confirm()

    def cancel(self):
        return self.getState().cancel()

    def expire(self):
        return self.getState().expire()
