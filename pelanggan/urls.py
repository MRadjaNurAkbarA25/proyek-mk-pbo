# pelanggan/urls.py
from django.urls import path
from . import (
    views,
    views_diagnosis,
    views_homeservice,
    views_pengajuan,
    views_riwayat,
)

urlpatterns = [
    path("dashboard/", views.dashboard_pelanggan, name="pelanggan_dashboard"),
    path("profil/edit/", views.edit_profil, name="edit_profil"),
    path("kendaraan/tambah/pilih/", views.pilih_tipe_kendaraan, name="pilih_tipe_kendaraan"),
    path("kendaraan/tambah/<str:tipe>/", views.tambah_kendaraan, name="tambah_kendaraan"),
    path("kendaraan/edit/<int:pk>/", views.edit_kendaraan, name="edit_kendaraan"),
    path("kendaraan/hapus/<int:pk>/", views.hapus_kendaraan, name="hapus_kendaraan"),
    path("kendaraan/", views.kendaraan_saya, name="kendaraan_saya"),
    path("home-service/pesan/", views_homeservice.pesan_home_service, name="pesan_home_service"),
    # FR-31: ajukan servis di bengkel, disetujui kasir
    path("ajukan-servis/", views_pengajuan.ajukan_servis, name="ajukan_servis"),
    path("pengajuan-saya/", views_pengajuan.pengajuan_saya, name="pengajuan_saya"),
    path("pengajuan-saya/<int:pk>/batalkan/", views_pengajuan.batalkan_pengajuan, name="batalkan_pengajuan"),
    path("pengajuan-saya/<int:pk>/tanggal/", views_pengajuan.ubah_tanggal_datang, name="ubah_tanggal_datang"),
    path("persetujuan-diagnosis/", views_diagnosis.persetujuan_diagnosis, name="persetujuan_diagnosis"),
    path("persetujuan-diagnosis/<int:pk>/", views_diagnosis.konfirmasi_diagnosis, name="konfirmasi_diagnosis"),
    path("riwayat/", views_riwayat.riwayat_service, name="riwayat_service"),
    path("riwayat/<int:pk>/", views_riwayat.riwayat_service_detail, name="riwayat_service_detail"),
]
