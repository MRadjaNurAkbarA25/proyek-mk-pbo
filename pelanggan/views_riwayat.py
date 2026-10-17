from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from servis.models import TransaksiServis
from .decorators import pelanggan_required


@login_required
@pelanggan_required
def riwayat_service(request):
    """Riwayat semua servis milik pelanggan, paling baru di urutan teratas."""
    profil = request.user.profil_pelanggan
    daftar = TransaksiServis.objects.filter(pelanggan=profil).select_related(
        "kendaraan", "mekanik", "mekanik__user", "pembayaran"
    ).order_by("-tanggal")

    status = request.GET.get("status", "").strip()
    pilihan_status = {value for value, _label in TransaksiServis.STATUS_CHOICES}
    if status in pilihan_status:
        daftar = daftar.filter(status=status)
    else:
        status = ""

    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)

    return render(request, "pelanggan/riwayat.html", {
        "daftar": halaman,
        "halaman": halaman,
        "status_terpilih": status,
        "pilihan_status": TransaksiServis.STATUS_CHOICES,
    })


@login_required
@pelanggan_required
def riwayat_service_detail(request, pk):
    """Detail transaksi dibatasi pada transaksi yang dimiliki pelanggan login."""
    profil = request.user.profil_pelanggan
    transaksi = get_object_or_404(
        TransaksiServis.objects.select_related(
            "kendaraan", "mekanik", "mekanik__user", "pembayaran"
        ).prefetch_related(
            "detail_servis__jenis_servis",
            "detail_sparepart__sparepart",
        ),
        pk=pk,
        pelanggan=profil,
    )
    return render(request, "pelanggan/riwayat_detail.html", {"transaksi": transaksi})
