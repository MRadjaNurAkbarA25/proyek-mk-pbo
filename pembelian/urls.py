"""URL app pembelian: Supplier dan Pembelian Sparepart (FR-35)."""
from django.urls import path

from . import views

app_name = "pembelian"

urlpatterns = [
    # Supplier
    path("supplier/", views.supplier_daftar, name="supplier_list"),
    path("supplier/tambah/", views.supplier_tambah, name="supplier_tambah"),
    path("supplier/<int:pk>/ubah/", views.supplier_ubah, name="supplier_ubah"),
    path("supplier/<int:pk>/status/", views.supplier_ubah_status, name="supplier_ubah_status"),
    # Pembelian
    path("", views.pembelian_daftar, name="pembelian_list"),
    path("catat/", views.pembelian_catat, name="pembelian_catat"),
    path("<int:pk>/", views.pembelian_detail, name="pembelian_detail"),
    path("<int:pk>/barang/tambah/", views.pembelian_tambah_barang, name="pembelian_tambah_barang"),
    path("<int:pk>/barang/<int:detail_pk>/hapus/", views.pembelian_hapus_barang, name="pembelian_hapus_barang"),
    path("<int:pk>/selesaikan/", views.pembelian_selesaikan, name="pembelian_selesaikan"),
    path("<int:pk>/hapus/", views.pembelian_hapus, name="pembelian_hapus"),
]