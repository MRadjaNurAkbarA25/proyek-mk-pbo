"""Angka di menu mekanik; query hanya untuk mekanik yang login."""

from accounts.models import Mekanik
from servis.models import TransaksiServis


def pesan_pelanggan(request):
    """Panggilan home service, antrian bengkel (0 saat cuti), dan pegangan yang perlu dilihat."""
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if getattr(pengguna, "role", None) != "MEKANIK":
        return {}
    mekanik = getattr(pengguna, "profil_mekanik", None)
    if mekanik is None:
        return {}
    return {
        "jumlah_panggilan_hs": TransaksiServis.panggilan_menunggu_untuk(mekanik).count(),
        "jumlah_antrian": (0 if mekanik.status == Mekanik.STATUS_CUTI
                           else TransaksiServis.antrian_bengkel().count()),
        "jumlah_perlu_dilihat": TransaksiServis.perlu_dilihat_mekanik(mekanik).count(),
        "jumlah_pesan_pelanggan": TransaksiServis.berpesan_baru_untuk_mekanik(mekanik).count(),
    }
