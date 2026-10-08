# pelanggan/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from accounts.models import User

def pelanggan_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        if not request.user.is_authenticated:
            messages.error(request, "Silakan login terlebih dahulu.")
            return redirect('login')
        
        if request.user.role != User.ROLE_PELANGGAN:
            messages.error(request, "Akses ditolak. Halaman ini khusus untuk Pelanggan.")

            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view