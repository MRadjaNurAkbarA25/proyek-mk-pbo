from accounts.decorators import role_required
from django.shortcuts import render

from kendaraan.models import Kendaraan
from mekanik.views import _antrian_bengkel
from servis.models import TransaksiServis

from .views_transaksi import untuk_tabel


@role_required("KASIR")
def dashboard_kasir(request):
    # Jumlah pengajuan dan bukti yang menunggu sudah ada di context processor
    # (jumlah_pengajuan_menunggu, jumlah_bukti_menunggu).
    return render(request, "kasir/dashboard.html", {
        # Antrian yang sama persis dengan yang dilihat mekanik.
        "jumlah_antrian": _antrian_bengkel().count(),
        "jumlah_belum_lunas": TransaksiServis.objects.filter(
            status=TransaksiServis.STATUS_SELESAI, pembayaran__isnull=True).count(),
        "transaksi_terbaru": untuk_tabel(TransaksiServis.objects.order_by("-tanggal"))[:5],
    })


@role_required("KASIR")
def cari_kendaraan(request):
    """FR-6: Kasir mencari kendaraan berdasarkan nomor polisi."""
    query = request.GET.get("q", "").strip()
    hasil = []
    if query:
        # Query lewat subclass supaya get_tipe() dan deskripsi_khusus() polymorphic
        for model in Kendaraan.model_subkelas():
            hasil += list(model.objects.filter(no_polisi__icontains=query).select_related("pelanggan__user"))
    return render(request, "kasir/cari_kendaraan.html", {"hasil": hasil, "query": query})
