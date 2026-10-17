"""Angka kecil yang perlu tampil di navbar kasir pada setiap halaman."""

from servis.models import PengajuanServis


def pengajuan_menunggu(request):
    """Jumlah pengajuan servis yang belum ditinjau, untuk badge di navbar kasir.

    Query hanya dijalankan untuk user kasir yang sudah login, jadi halaman
    publik dan halaman role lain tidak terkena tambahan query.
    """
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
