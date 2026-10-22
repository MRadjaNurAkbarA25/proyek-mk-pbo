"""Angka kecil di menu mekanik pada setiap halaman (QoL A4).

Pola yang sama dengan kasir.context_processors dan pelanggan.context_processors:
query hanya berjalan untuk mekanik yang sudah login.
"""

from servis.models import TransaksiServis


def pesan_pelanggan(request):
    """jumlah_pesan_pelanggan: pekerjaan mekanik ini yang punya pesan pelanggan belum dibaca."""
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if getattr(pengguna, "role", None) != "MEKANIK":
        return {}
    mekanik = getattr(pengguna, "profil_mekanik", None)
    if mekanik is None:
        return {}
    return {"jumlah_pesan_pelanggan": TransaksiServis.berpesan_baru_untuk_mekanik(mekanik).count()}
