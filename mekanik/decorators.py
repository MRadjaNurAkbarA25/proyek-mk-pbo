# mekanik/decorators.py
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from accounts.models import Mekanik, User


def mekanik_required(view_func):
    """Hanya role MEKANIK (FR-3, NFR-5). Profil Mekanik dibuat otomatis jika belum ada."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Silakan login terlebih dahulu.")
            return redirect("login")
        if request.user.role != User.ROLE_MEKANIK:
            messages.error(request, "Akses ditolak. Halaman ini khusus untuk Mekanik.")
            return redirect("dashboard")
        request.mekanik, _ = Mekanik.objects.get_or_create(user=request.user)
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    """Hanya role ADMIN (superuser Django juga diizinkan)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Silakan login terlebih dahulu.")
            return redirect("login")
        if not (request.user.is_superuser or request.user.role == User.ROLE_ADMIN):
            messages.error(request, "Akses ditolak. Halaman ini khusus untuk Admin.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped
