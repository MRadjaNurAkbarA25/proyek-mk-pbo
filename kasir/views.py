from accounts.decorators import role_required
from django.shortcuts import render

from accounts.decorators import role_required
from kendaraan.models import Mobil, Motor, Truk


@role_required("KASIR")
def dashboard_kasir(request):
    return render(request, "kasir/dashboard.html", {"user": request.user})


@role_required("KASIR")
def cari_kendaraan(request):
    """FR-6: Kasir mencari kendaraan berdasarkan nomor polisi."""
    query = request.GET.get("q", "").strip()
    hasil = []
    if query:
        # Query lewat subclass supaya get_tipe() dan deskripsi_khusus() polymorphic
        for model in (Mobil, Motor, Truk):
            hasil += list(model.objects.filter(no_polisi__icontains=query).select_related("pelanggan__user"))
    return render(request, "kasir/cari_kendaraan.html", {"hasil": hasil, "query": query})