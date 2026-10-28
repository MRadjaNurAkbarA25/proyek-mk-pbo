"""Badge Peringatan Stok untuk role yang punya menu itu (kasir, mekanik, admin)."""

from .models import Sparepart


def stok_kritis(request):
    """jumlah_stok_kritis (Kosong/Minim) dan warnanya: merah bila ada yang Kosong, kuning bila hanya Minim."""
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if not (pengguna.role in ("KASIR", "MEKANIK", "ADMIN") or pengguna.is_superuser):
        return {}
    kritis = Sparepart.kritis()
    return {
        "jumlah_stok_kritis": kritis.count(),
        "warna_stok_kritis": "merah" if kritis.filter(stok__lte=0).exists() else "kuning",
    }
