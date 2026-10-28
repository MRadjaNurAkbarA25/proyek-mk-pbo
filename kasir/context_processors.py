"""Angka kecil yang perlu tampil di navbar kasir pada setiap halaman."""

from servis.models import PengajuanServis


def pengajuan_menunggu(request):
    """Badge jumlah pengajuan yang belum ditinjau; query hanya untuk kasir yang login."""
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if getattr(pengguna, "role", None) != "KASIR":
        return {}
    return {
        "jumlah_pengajuan_menunggu": PengajuanServis.objects.filter(
            status=PengajuanServis.STATUS_MENUNGGU
        ).count()
    }
