"""Langkah progres satu transaksi, dilihat dari sisi mekanik.

Dipakai kartu "Pekerjaan Saat Ini" di beranda mekanik.
"""
from servis.models import TransaksiServis as T

# Urutan langkah: nama tampilan, ikon, dan status yang menandai langkah itu sedang berjalan.
LANGKAH = [
    ("Permintaan", "i-flag", [T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK]),
    ("Pemeriksaan", "i-build", [T.STATUS_MENUNGGU]),
    ("Persetujuan", "i-assignment", [T.STATUS_MENUNGGU_KONFIRMASI]),
    ("Perbaikan", "i-kerja", [T.STATUS_DIKERJAKAN]),
    ("Selesai", "i-check", [T.STATUS_SELESAI]),
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
