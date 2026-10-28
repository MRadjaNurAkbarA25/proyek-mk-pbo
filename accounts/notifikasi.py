"""Angka badge semua role: context processor yang sama dipakai template dan endpoint /accounts/notifikasi/."""

from kasir.context_processors import pengajuan_menunggu
from mekanik.context_processors import pesan_pelanggan
from pelanggan.context_processors import kabar_pelanggan
from pembayaran.context_processors import bukti_menunggu
from pembelian.context_processors import pembelian_draf
from sparepart.context_processors import stok_kritis

PEMBERI_ANGKA = (pengajuan_menunggu, pesan_pelanggan, kabar_pelanggan, bukti_menunggu, stok_kritis, pembelian_draf)


def angka_badge(request):
    """Gabungan angka untuk role yang login; tiap context processor memeriksa role-nya sendiri."""
    hasil = {}
    for pemberi in PEMBERI_ANGKA:
        hasil.update(pemberi(request))
    return hasil
