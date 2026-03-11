from functools import wraps
from django.shortcuts import redirect
from functools import wraps
from django.shortcuts import redirect

def org_staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect('login')

        # Superuser allowed
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        profile = getattr(request.user, 'userprofile', None)

        if not profile:
            return redirect('dashboard')

        if profile.role not in ['org_admin', 'staff', 'pharmacist']:
            return redirect('dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper

def org_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        # Superuser allowed
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if request.user.userprofile.role != 'org_admin':
            return redirect('dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper