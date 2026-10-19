"""Angka kecil di menu pelanggan pada setiap halaman.

Pola yang sama dengan kasir.context_processors: query hanya berjalan untuk
pelanggan yang sudah login, jadi halaman publik dan role lain tidak kena.
"""

from servis.models import TransaksiServis


def kabar_pelanggan(request):
    """Dua angka untuk menu pelanggan.

    jumlah_menunggu_persetujuan: diagnosis yang menunggu jawaban pelanggan.
        Mekanik tidak boleh mulai bekerja sebelum dijawab.
    jumlah_kabar_riwayat: transaksi yang linimasanya punya kabar belum
        dibaca (TransaksiServis.berkabar_baru_untuk).
    """
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
