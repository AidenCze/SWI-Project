from django.db import models
from django.contrib.auth.models import User

class ParkingLot(models.Model):
    name = models.CharField(max_length=100, verbose_name="Název parkoviště")
    floor = models.IntegerField(default=0, verbose_name="Patro")

    class Meta:
        verbose_name = "Parkoviště"
        verbose_name_plural = "Parkoviště"

    def __str__(self):
        return f"{self.name} (Patro {self.floor})"


class ParkingSpot(models.Model):
    class SpotType(models.TextChoices):
        NORMAL = 'NORMAL', 'Běžné'
        DISABLED = 'DISABLED_ONLY', 'Vyhrazeno pro ZTP'
        EV = 'EV_ONLY', 'Nabíjecí stanice (EV)'

    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='spots', verbose_name="Parkoviště")
    number = models.CharField(max_length=10, unique=True, verbose_name="Číslo místa")
    spot_type = models.CharField(max_length=20, choices=SpotType.choices, default=SpotType.NORMAL, verbose_name="Typ místa")
    is_active = models.BooleanField(default=True, verbose_name="Aktivní pro rezervace")

    class Meta:
        verbose_name = "Parkovací místo"
        verbose_name_plural = "Parkovací místa"

    def __str__(self):
        return f"{self.number} ({self.get_spot_type_display()})"


class Reservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', verbose_name="Zaměstnanec")
    spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, related_name='reservations', verbose_name="Parkovací místo")
    
    date = models.DateField(verbose_name="Datum rezervace")
    start_time = models.TimeField(verbose_name="Od")
    end_time = models.TimeField(verbose_name="Do")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rezervace"
        verbose_name_plural = "Rezervace"

    def __str__(self):
        return f"{self.user.username} - {self.spot.number} ({self.date})"