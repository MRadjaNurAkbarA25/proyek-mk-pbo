"""Aturan paginasi bersama, supaya jumlah baris dan navigasinya seragam di semua daftar.

Pemakaian: `halaman = halaman_dari(request, queryset, PER_HALAMAN_TABEL)`.
"""

from django.core.paginator import Paginator

# Tabel biasa: 10 baris masih nyaman dibaca tanpa scroll panjang.
PER_HALAMAN_TABEL = 10
# Daftar sparepart lebih padat (satu baris = satu barang), boleh lebih banyak.
PER_HALAMAN_PADAT = 15
# Antrian mekanik memakai kartu 3 kolom, jadi kelipatan 3 supaya baris terakhir rapi.
PER_HALAMAN_KARTU = 9


def halaman_dari(request, daftar, per_halaman=PER_HALAMAN_TABEL):
    """Potong `daftar` sesuai ?page=; get_page() membuat nomor tak sah jatuh ke halaman pertama/terakhir."""
    paginator = Paginator(daftar, per_halaman)
    halaman = paginator.get_page(request.GET.get("page"))

    # Deretan nomor yang dipendekkan: 1 … 4 [5] 6 … 20, supaya navigasi tidak
    # melebar saat datanya ratusan halaman. Hasilnya berisi angka dan ELLIPSIS.
    halaman.rentang_nomor = list(
        paginator.get_elided_page_range(halaman.number, on_each_side=1, on_ends=1)
    )
    # Ditempelkan ke objek halaman supaya template bisa membandingkannya tanpa
    # perlu mengimpor Paginator.
    halaman.elipsis = Paginator.ELLIPSIS
    return halaman
