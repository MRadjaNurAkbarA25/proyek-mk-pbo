from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .beranda import WARNA_BADGE
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from servis.models import TransaksiServis
from accounts.decorators import pelanggan_required


@login_required
@pelanggan_required
def riwayat_service(request):
    """Riwayat semua servis milik pelanggan, paling baru di urutan teratas."""
    # FR-31 C: sapu dulu, supaya pelanggan tidak melihat transaksi yang
    # seharusnya sudah batal hanya karena kasirnya belum membuka halaman.
    TransaksiServis.sapu_kedatangan_lewat()

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

    # FR-32: baris yang punya kabar belum dibaca diberi penanda. Satu query
    # untuk semua baris, bukan satu per baris.
    kabar_baru = set(
        TransaksiServis.berkabar_baru_untuk(profil).values_list("pk", flat=True)
    )

    return render(request, "pelanggan/riwayat.html", {
        "kabar_baru": kabar_baru,
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
    # FR-32: dibuka = sudah dibaca. Dilakukan sebelum render supaya angka di
    # menu pada halaman ini sendiri sudah tidak menghitung transaksi ini.
    transaksi.tandai_dibaca_pelanggan()
    return render(request, "pelanggan/riwayat_detail.html", {
        "transaksi": transaksi,
        "warna_status": WARNA_BADGE.get(transaksi.status, "abu"),
        # select_related("oleh"): tiap baris linimasa menampilkan nama
        # penulisnya; tanpa ini satu query tambahan per baris.
        "pembaruan": transaksi.pembaruan.select_related("oleh"),
    })
