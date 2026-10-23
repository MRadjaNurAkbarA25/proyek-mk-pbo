"""Empat halaman laporan admin (FR-27 sampai FR-30).

Seluruh perhitungannya ada di hierarki class Laporan (laporan/laporan.py),
sesuai rancangan dokumen bagian 5E. View di sini sengaja dibuat tipis:
tugasnya cuma memeriksa hak akses, memilih class laporan mana yang dipakai,
lalu menyerahkan hasilnya ke template.

Perhatikan keempat fungsi di bawah bentuknya sama persis. Itu memang
polimorfismenya: yang berbeda hanya class yang disebut, karena keempat
class itu menjawab `.konteks()` dengan caranya masing-masing.
"""
from django.shortcuts import render

from accounts.decorators import role_required
from laporan.laporan import (
    LaporanMekanik, LaporanPembelian, LaporanPendapatan, LaporanServis, LaporanStok,
)


@role_required("ADMIN")
def laporan_transaksi(request):
    return render(request, "adminpanel/laporan_transaksi.html",
                  LaporanServis(request).konteks())


@role_required("ADMIN")
def laporan_pendapatan(request):
    return render(request, "adminpanel/laporan_pendapatan.html",
                  LaporanPendapatan(request).konteks())


@role_required("ADMIN")
def laporan_stok(request):
    return render(request, "adminpanel/laporan_stok.html",
                  LaporanStok(request).konteks())


@role_required("ADMIN")
def laporan_mekanik(request):
    return render(request, "adminpanel/laporan_mekanik.html",
                  LaporanMekanik(request).konteks())


@role_required("ADMIN")
def laporan_pembelian(request):
    return render(request, "adminpanel/laporan_pembelian.html",
                  LaporanPembelian(request).konteks())
