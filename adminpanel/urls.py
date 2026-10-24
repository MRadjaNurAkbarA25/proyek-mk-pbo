from django.urls import path

from . import views, views_akun, views_kendaraan, views_laporan, views_pelanggan

urlpatterns = [
    path("dashboard/", views.dashboard_admin, name="admin_dashboard"),
    path("laporan/transaksi/", views_laporan.laporan_transaksi, name="laporan_transaksi"),
    path("laporan/pendapatan/", views_laporan.laporan_pendapatan, name="laporan_pendapatan"),
    path("laporan/stok/", views_laporan.laporan_stok, name="laporan_stok"),
    path("laporan/mekanik/", views_laporan.laporan_mekanik, name="laporan_mekanik"),
    path("laporan/pembelian/", views_laporan.laporan_pembelian, name="laporan_pembelian"),
    path("kendaraan/", views_kendaraan.daftar_kendaraan, name="kelola_kendaraan"),
    path("pelanggan/", views_pelanggan.daftar_pelanggan, name="kelola_pelanggan"),
    path("pelanggan/tambah/", views_pelanggan.tambah_pelanggan, name="kelola_pelanggan_tambah"),
    path("pelanggan/<int:pk>/ubah/", views_pelanggan.ubah_pelanggan, name="kelola_pelanggan_ubah"),
    path("kasir/", views_akun.daftar_kasir, name="kelola_kasir"),
    path("kasir/tambah/", views_akun.tambah_kasir, name="kelola_kasir_tambah"),
    path("kasir/<int:pk>/ubah/", views_akun.ubah_kasir, name="kelola_kasir_ubah"),
    # Nonaktifkan / aktifkan akun kasir dan mekanik (bukan hapus).
    path("akun/<int:pk>/status/", views_akun.ubah_status_akun, name="akun_ubah_status"),
]
