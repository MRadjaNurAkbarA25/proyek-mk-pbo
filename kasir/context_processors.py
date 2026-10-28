"""Angka kecil yang perlu tampil di navbar kasir pada setiap halaman."""

from servis.models import PengajuanServis, TransaksiServis


def pengajuan_menunggu(request):
    """Badge pengajuan yang belum ditinjau dan transaksi yang perlu tindakan kasir; hanya untuk kasir yang login."""
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if getattr(pengguna, "role", None) != "KASIR":
        return {}
    return {
        "jumlah_pengajuan_menunggu": PengajuanServis.objects.filter(
            status=PengajuanServis.STATUS_MENUNGGU
        ).count(),
        "jumlah_perlu_tindakan": TransaksiServis.perlu_tindakan_kasir().count(),
    }
