"""Angka bukti pembayaran non-tunai yang menunggu, untuk badge di menu kasir/admin."""

from .models import BuktiPembayaran


def bukti_menunggu(request):
    """Hanya dihitung untuk kasir/admin yang login, seperti badge pengajuan."""
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if not (pengguna.role in ("KASIR", "ADMIN") or pengguna.is_superuser):
        return {}
    return {
        "jumlah_bukti_menunggu": BuktiPembayaran.objects.filter(
            status=BuktiPembayaran.STATUS_MENUNGGU
        ).count()
    }
