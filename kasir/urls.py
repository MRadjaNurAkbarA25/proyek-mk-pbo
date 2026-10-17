from django.urls import path
from . import views, views_pengajuan, views_transaksi

urlpatterns = [
    path("dashboard/", views.dashboard_kasir, name="kasir_dashboard"),
    path("kendaraan/cari/", views.cari_kendaraan, name="kasir_cari_kendaraan"),

    # FR-11: Buat & lihat transaksi servis
    path("transaksi/buat/", views_transaksi.buat_transaksi, name="kasir_transaksi_buat"),
    path("transaksi/", views_transaksi.daftar_transaksi, name="kasir_transaksi_daftar"),
    path("transaksi/<int:pk>/", views_transaksi.detail_transaksi, name="kasir_transaksi_detail"),
    path("transaksi/<int:pk>/tiba/", views_transaksi.tandai_kendaraan_tiba, name="kasir_tandai_tiba"),

    # FR-31: tinjau pengajuan servis dari pelanggan
    path("pengajuan/", views_pengajuan.daftar_pengajuan, name="kasir_pengajuan_daftar"),
    path("pengajuan/<int:pk>/terima/", views_pengajuan.terima_pengajuan, name="kasir_pengajuan_terima"),
    path("pengajuan/<int:pk>/tolak/", views_pengajuan.tolak_pengajuan, name="kasir_pengajuan_tolak"),
]
