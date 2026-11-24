from django.contrib import admin
from .models import ParkingLot, ParkingSpot, Reservation

@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('name', 'floor', 'layout_rows', 'layout_columns')

@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    # Určuje, jaké sloupečky uvidíš v přehledu všech míst
    list_display = ('number', 'lot', 'layout_row', 'layout_column', 'spot_type', 'is_active')
    # Přidá boční panel pro rychlé filtrování
    list_filter = ('is_active', 'spot_type', 'lot')
    search_fields = ('number',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'spot', 'date', 'start_time', 'end_time', 'state_code')
    list_filter = ('date', 'spot', 'state_code')
    search_fields = ('user__username', 'spot__number')