from django.urls import path
from . import views, views_admin, views_jenis

urlpatterns = [
    # --- sisi Mekanik ---
    path("dashboard/", views.dashboard_mekanik, name="mekanik_dashboard"),
    path("status/", views.ubah_ketersediaan, name="mekanik_ubah_status"),
    path("antrian/", views.antrian_servis, name="mekanik_antrian"),
    path("servis/<int:pk>/", views.detail_servis, name="mekanik_detail"),
    path("servis/<int:pk>/ambil/", views.ambil_pekerjaan, name="mekanik_ambil"),
    path("servis/<int:pk>/terima/", views.terima_home_service, name="mekanik_terima"),
    path("servis/<int:pk>/tolak/", views.tolak_home_service, name="mekanik_tolak"),
    path("servis/<int:pk>/diagnosis/", views.input_diagnosis, name="mekanik_diagnosis"),
    path("servis/<int:pk>/layanan/", views.tambah_layanan, name="mekanik_tambah_layanan"),
    path("servis/<int:pk>/sparepart/", views.tambah_sparepart, name="mekanik_tambah_sparepart"),
    path("servis/<int:pk>/selesai/", views.selesaikan_servis, name="mekanik_selesai"),
    path("servis/<int:pk>/lanjut-bengkel/", views.lanjut_di_bengkel, name="mekanik_lanjut_bengkel"),
    # --- sisi Admin: kelola data mekanik (FR-8, FR-9) ---
    path("kelola/", views_admin.daftar_mekanik, name="kelola_mekanik"),
    path("kelola/tambah/", views_admin.tambah_mekanik, name="kelola_mekanik_tambah"),
    path("kelola/<int:pk>/ubah/", views_admin.ubah_mekanik, name="kelola_mekanik_ubah"),
    path("kelola/<int:pk>/hapus/", views_admin.hapus_mekanik, name="kelola_mekanik_hapus"),
    # --- sisi Admin: kelola Jenis Servis ---
    path("jenis/", views_jenis.daftar_jenis, name="kelola_jenis"),
    path("jenis/tambah/", views_jenis.tambah_jenis, name="kelola_jenis_tambah"),
    path("jenis/<int:pk>/ubah/", views_jenis.ubah_jenis, name="kelola_jenis_ubah"),
    path("jenis/<int:pk>/hapus/", views_jenis.hapus_jenis, name="kelola_jenis_hapus"),
]
