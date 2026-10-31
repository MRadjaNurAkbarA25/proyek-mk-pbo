from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PesanPelangganForm
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from servis.models import TransaksiServis
from accounts.decorators import pelanggan_required


@login_required
@pelanggan_required
def riwayat_service(request):
    """Riwayat semua servis milik pelanggan, yang terakhir ada aktivitasnya di urutan teratas."""
    # FR-31 C: sapu dulu, supaya pelanggan tidak melihat transaksi yang
    # seharusnya sudah batal hanya karena kasirnya belum membuka halaman.
    TransaksiServis.sapu_kedatangan_lewat()

    profil = request.user.profil_pelanggan
    daftar = TransaksiServis.dengan_status_bayar(TransaksiServis.dengan_aktivitas_terakhir(
        TransaksiServis.objects.filter(pelanggan=profil)
    )).select_related(
        "kendaraan", "mekanik", "mekanik__user"
    ).order_by("-terakhir_diperbarui", "-pk")

    status = request.GET.get("status", "").strip()
    pilihan_status = {value for value, _label in TransaksiServis.STATUS_CHOICES}
    if status in pilihan_status:
        daftar = daftar.filter(status=status)
    else:
        status = ""

    # Pencarian: kode transaksi, merk, model, atau nomor polisi kendaraan.
    q = request.GET.get("q", "").strip()
    if q:
        daftar = daftar.filter(
            Q(kode_transaksi__icontains=q)
            | Q(kendaraan__merk__icontains=q)
            | Q(kendaraan__model_kendaraan__icontains=q)
            | Q(kendaraan__no_polisi__icontains=q)
        )

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
        "q": q,
        "pilihan_status": TransaksiServis.STATUS_CHOICES,
    })


@login_required
@pelanggan_required
def riwayat_service_detail(request, pk):
    """Detail transaksi dibatasi pada transaksi yang dimiliki pelanggan login."""
    profil = request.user.profil_pelanggan
    transaksi = get_object_or_404(
        TransaksiServis.dengan_aktivitas_terakhir(TransaksiServis.objects).select_related(
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
        # select_related("oleh"): tiap baris linimasa menampilkan nama
        # penulisnya; tanpa ini satu query tambahan per baris.
        "pembaruan": transaksi.pembaruan.select_related("oleh"),
        "form_pesan": PesanPelangganForm() if transaksi.bisa_ditanya_pelanggan else None,
        # Bukti non-tunai terbaru: menunggu, atau ditolak beserta alasannya.
        "bukti_terakhir": transaksi.bukti_pembayaran.first(),
    })


@login_required
@pelanggan_required
@require_POST
def kirim_pesan(request, pk):
    """QoL A4: pelanggan menulis satu kalimat ke linimasa; transaksi orang lain 404."""
    profil = request.user.profil_pelanggan
    transaksi = get_object_or_404(TransaksiServis, pk=pk, pelanggan=profil)
    form = PesanPelangganForm(request.POST)
    if not form.is_valid():
        for galat in form.errors.get("keterangan", []):
            messages.error(request, galat)
        return redirect("riwayat_service_detail", pk=pk)
    try:
        transaksi.tulis_pesan_pelanggan(profil, form.cleaned_data["keterangan"])
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        messages.success(request, "Pesan terkirim ke mekanik. Jawabannya akan muncul di linimasa ini.")
    return redirect("riwayat_service_detail", pk=pk)
