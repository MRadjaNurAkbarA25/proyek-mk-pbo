"""Angka kecil di menu pelanggan; query hanya berjalan untuk pelanggan yang login."""

from servis.models import TransaksiServis


def kabar_pelanggan(request):
    """jumlah_menunggu_persetujuan (diagnosis menunggu jawaban) dan jumlah_kabar_riwayat (kabar belum dibaca)."""
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if getattr(pengguna, "role", None) != "PELANGGAN":
        return {}
    profil = getattr(pengguna, "profil_pelanggan", None)
    if profil is None:
        return {}
    return {
        "jumlah_menunggu_persetujuan": TransaksiServis.objects.filter(
            pelanggan=profil, status=TransaksiServis.STATUS_MENUNGGU_KONFIRMASI
        ).count(),
        "jumlah_kabar_riwayat": TransaksiServis.berkabar_baru_untuk(profil).count(),
    }
