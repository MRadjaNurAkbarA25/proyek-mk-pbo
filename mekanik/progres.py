"""Langkah progres satu transaksi, dilihat dari sisi mekanik.

Dipakai kartu "Pekerjaan Saat Ini" di beranda mekanik.
"""
from servis.models import LABEL_TAHAP, PembaruanServis as P, TransaksiServis as T

# Urutan langkah: nama tampilan, ikon, dan status yang menandai langkah itu sedang berjalan.
#
# Nama langkahnya diambil dari LABEL_TAHAP di servis/models.py, bukan diketik
# ulang di sini. Linimasa pelanggan (FR-32) memakai daftar yang sama, jadi
# kedua tampilan tidak mungkin menyebut tahap yang sama dengan nama berbeda.
LANGKAH = [
    (LABEL_TAHAP[P.TAHAP_PERMINTAAN], "i-flag", [T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK]),
    (LABEL_TAHAP[P.TAHAP_PEMERIKSAAN], "i-build", [T.STATUS_MENUNGGU]),
    (LABEL_TAHAP[P.TAHAP_PERSETUJUAN], "i-assignment", [T.STATUS_MENUNGGU_KONFIRMASI]),
    (LABEL_TAHAP[P.TAHAP_PERBAIKAN], "i-kerja", [T.STATUS_DIKERJAKAN]),
    (LABEL_TAHAP[P.TAHAP_SELESAI], "i-check", [T.STATUS_SELESAI]),
]


def langkah_servis(transaksi):
    """Kembalikan daftar langkah dengan penanda 'selesai' / 'sekarang'."""
    if transaksi is None:
        return []

    urutan = [status for _, _, daftar in LANGKAH for status in daftar]
    try:
        posisi = urutan.index(transaksi.status)
    except ValueError:  # DIBATALKAN atau status lain: tidak ada langkah berjalan
        posisi = -1

    hasil = []
    for nomor, (nama, ikon, _) in enumerate(LANGKAH):
        if posisi == -1:
            kondisi = ""
        elif nomor < posisi:
            kondisi = "selesai"
        elif nomor == posisi:
            kondisi = "sekarang"
        else:
            kondisi = ""
        hasil.append({"nama": nama, "ikon": ikon, "kondisi": kondisi})
    return hasil
