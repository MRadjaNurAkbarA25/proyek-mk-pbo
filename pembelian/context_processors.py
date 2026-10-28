"""Badge Pembelian (jumlah draf) di menu admin."""

from .models import PembelianSparepart


def pembelian_draf(request):
    pengguna = getattr(request, "user", None)
    if not (pengguna and pengguna.is_authenticated):
        return {}
    if not (pengguna.role == "ADMIN" or pengguna.is_superuser):
        return {}
    return {"jumlah_pembelian_draf": PembelianSparepart.draf().count()}
