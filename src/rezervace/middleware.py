from django.shortcuts import redirect
from django.urls import reverse


class PasswordChangeRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'parksys_profile', None)
            allowed_paths = {
                reverse('password_change'),
                reverse('logout'),
                '/static/',
                '/admin/',
            }
            if (
                profile
                and profile.must_change_password
                and not request.path.startswith(tuple(allowed_paths))
            ):
                return redirect('password_change')

        return self.get_response(request)
