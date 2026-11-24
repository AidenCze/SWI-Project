"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm

from rezervace import views as rezervace_views

# Úprava výchozího formuláře pro přidání Bootstrap CSS tříd
class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        authentication_form=CustomLoginForm
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password/change/', rezervace_views.password_change_view, name='password_change'),
    path('dashboard/', rezervace_views.dashboard_view, name='dashboard'),
    
    # Nový řádek pro vytvoření rezervace
    path('reservations/new/', rezervace_views.reservation_create_view, name='reservation_create'),
    path('reservations/new/grid/', rezervace_views.reservation_grid_fragment_view, name='reservation_grid_fragment'),
    path('reservations/lock/', rezervace_views.reservation_lock_view, name='reservation_lock'),
    path('reservations/<int:reservation_id>/delete/', rezervace_views.reservation_delete_view, name='reservation_delete'),
    path('manage/', rezervace_views.admin_dashboard_view, name='admin_dashboard'),
    path('manage/users/', rezervace_views.admin_users_view, name='admin_users'),
    path('manage/users/add/', rezervace_views.admin_user_create_view, name='admin_user_create'),
    path('manage/users/<int:user_id>/delete/', rezervace_views.admin_user_delete_view, name='admin_user_delete'),
    path('manage/reservations/', rezervace_views.admin_reservations_view, name='admin_reservations'),
    path('manage/reservations/<int:reservation_id>/delete/', rezervace_views.admin_reservation_delete_view, name='admin_reservation_delete'),
    path('manage/lots/', rezervace_views.admin_lots_view, name='admin_lots'),
    path('manage/lots/add/', rezervace_views.admin_lot_create_view, name='admin_lot_create'),
    path('manage/lots/<int:lot_id>/edit/', rezervace_views.admin_lot_edit_view, name='admin_lot_edit'),
    path('manage/lots/<int:lot_id>/delete/', rezervace_views.admin_lot_delete_view, name='admin_lot_delete'),
    path('manage/lots/<int:lot_id>/spots/', rezervace_views.admin_spots_view, name='admin_spots'),
    path('manage/lots/<int:lot_id>/spots/add/', rezervace_views.admin_spot_create_view, name='admin_spot_create'),
    path('manage/lots/<int:lot_id>/spots/bulk/', rezervace_views.admin_spots_bulk_create_view, name='admin_spots_bulk_create'),
    path('manage/lots/<int:lot_id>/spots/<int:spot_id>/edit/', rezervace_views.admin_spot_edit_view, name='admin_spot_edit'),
    path('manage/lots/<int:lot_id>/spots/<int:spot_id>/delete/', rezervace_views.admin_spot_delete_view, name='admin_spot_delete'),
]