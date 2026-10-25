from django.urls import path

from . import views

urlpatterns = [
    path("transaksi/<int:pk>/bayar/", views.bayar_transaksi, name="pembayaran_bayar"),
    path("transaksi/<int:pk>/cash-mekanik/", views.cash_mekanik, name="pembayaran_cash_mekanik"),
    path("transaksi/<int:pk>/non-tunai/", views.bayar_nontunai, name="pembayaran_nontunai"),
    path("bukti/<int:pk>/berkas/", views.bukti_berkas, name="pembayaran_bukti_berkas"),
    path("verifikasi/", views.verifikasi_daftar, name="pembayaran_verifikasi_daftar"),
    path("verifikasi/<int:pk>/", views.verifikasi_detail, name="pembayaran_verifikasi_detail"),
    path("verifikasi/<int:pk>/setujui/", views.verifikasi_setujui, name="pembayaran_verifikasi_setujui"),
    path("verifikasi/<int:pk>/tolak/", views.verifikasi_tolak, name="pembayaran_verifikasi_tolak"),
    path("nota/<int:pk>/", views.nota_pembayaran, name="pembayaran_nota"),
]
