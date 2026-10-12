from django.urls import path

from . import views

urlpatterns = [
    path("transaksi/<int:pk>/bayar/", views.bayar_transaksi, name="pembayaran_bayar"),
    path("nota/<int:pk>/", views.nota_pembayaran, name="pembayaran_nota"),
]
