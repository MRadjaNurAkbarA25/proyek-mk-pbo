from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*roles):
    """
    Batasi view hanya untuk role tertentu, contoh: @role_required("ADMIN", "KASIR").
    Superuser Django selalu diizinkan (diperlakukan sebagai Admin).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Silakan login terlebih dahulu.")
                return redirect("login")
            if not (request.user.is_superuser or request.user.role in roles):
                messages.error(request, "Akses ditolak. Anda tidak berhak membuka halaman ini.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator