"""Pembatasan halaman per role; satu-satunya tempat aturan ini ditulis.

Superuser dianggap Admin, tapi tidak boleh membuka halaman pelanggan/mekanik
karena tidak punya profilnya (halamannya akan error 500).
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from accounts.models import Mekanik, User


def role_required(*roles, izinkan_superuser=True):
    """Batasi view untuk role tertentu, contoh: @role_required("ADMIN", "KASIR")."""
    label = dict(User.ROLE_CHOICES)
    pesan_tolak = (
        f"Akses ditolak. Halaman ini khusus untuk {label.get(roles[0], roles[0])}."
        if len(roles) == 1
        else "Akses ditolak. Anda tidak berhak membuka halaman ini."
    )

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            pengguna = request.user
            if not pengguna.is_authenticated:
                messages.error(request, "Silakan login terlebih dahulu.")
                return redirect("login")
            boleh = pengguna.role in roles or (izinkan_superuser and pengguna.is_superuser)
            if not boleh:
                messages.error(request, pesan_tolak)
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


#: Halaman admin. Superuser ikut diizinkan.
admin_required = role_required(User.ROLE_ADMIN)

#: Halaman pelanggan. Superuser tidak diizinkan (tidak punya profil pelanggan).
pelanggan_required = role_required(User.ROLE_PELANGGAN, izinkan_superuser=False)


def mekanik_required(view_func):
    """Halaman mekanik (FR-3, NFR-5); profil Mekanik dipasang di request.mekanik."""
    @wraps(view_func)
    def _pasang_profil(request, *args, **kwargs):
        request.mekanik, _ = Mekanik.objects.get_or_create(user=request.user)
        return view_func(request, *args, **kwargs)

    return role_required(User.ROLE_MEKANIK, izinkan_superuser=False)(_pasang_profil)
