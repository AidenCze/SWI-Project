from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ParkingSpot

# Dekorátor zajistí, že nepřihlášeného uživatele to automaticky přesměruje na login
@login_required
def dashboard_view(request):
    # Vytáhneme z databáze všechna místa, která jsou aktivní
    spots = ParkingSpot.objects.filter(is_active=True)
    
    # Slovník 'context' obsahuje všechna data, která posíláme do HTML
    context = {
        'spots': spots,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def reservation_create_view(request):
    # Zatím jen vrátí prázdnou šablonu, logiku pro ukládání přidáme později
    return render(request, 'reservation_form.html')