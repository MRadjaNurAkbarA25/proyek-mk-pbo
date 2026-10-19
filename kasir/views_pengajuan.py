"""FR-31 sisi Kasir: meninjau pengajuan servis yang dikirim pelanggan.

Terima  -> dibuatkan TransaksiServis tipe DI_BENGKEL, langsung masuk antrian
           bengkel milik mekanik (/mekanik/antrian/).
Tolak   -> pengajuan ditutup dengan alasan yang bisa dibaca pelanggan.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from pelanggan.forms_pengajuan import TolakPengajuanForm
from servis.models import PengajuanServis, TransaksiServis

RELASI = (
    "pelanggan__user",
    "kendaraan__mobil",
    "kendaraan__motor",
    "kendaraan__truk",
    "transaksi",
    "diproses_oleh",
)


@role_required("KASIR")
def daftar_pengajuan(request):
    """Daftar pengajuan. Default menampilkan yang masih menunggu keputusan.

    Dibedakan antara "parameter status tidak ada" (kasir baru membuka menu ->
    tampilkan yang menunggu) dan "status sengaja dikosongkan" (kasir memilih
    '— Semua —' lalu menekan Tampilkan -> tampilkan semua). Kalau keduanya
    disamakan, pilihan '— Semua —' tidak akan pernah berfungsi.
    """
    # FR-31 C: batalkan dulu transaksi yang kendaraannya tidak kunjung datang,
    # supaya daftar di bawah ini tidak menampilkan pengajuan yang transaksinya
    # sebenarnya sudah kedaluwarsa.
    TransaksiServis.sapu_kedatangan_lewat()

    if "status" in request.GET:
        status = (request.GET.get("status") or "").strip().upper()
    else:
        status = PengajuanServis.STATUS_MENUNGGU

    if status and status not in dict(PengajuanServis.STATUS_CHOICES):
        status = ""

    daftar = PengajuanServis.objects.select_related(*RELASI)
    if status:
        daftar = daftar.filter(status=status)

    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)
    return render(request, "kasir/pengajuan_daftar.html", {
        "daftar": halaman,
        "halaman": halaman,
        "status_terpilih": status,
        "status_choices": PengajuanServis.STATUS_CHOICES,
        "jumlah_menunggu": PengajuanServis.objects.filter(
            status=PengajuanServis.STATUS_MENUNGGU
        ).count(),
        "form_tolak": TolakPengajuanForm(),
    })


@require_POST
@role_required("KASIR")
def terima_pengajuan(request, pk):
    pengajuan = get_object_or_404(PengajuanServis, pk=pk)
    try:
        transaksi = pengajuan.terima(request.user)
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
        return redirect("kasir_pengajuan_daftar")

    messages.success(
        request,
        f"Pengajuan diterima. Transaksi {transaksi.kode_transaksi} dibuat dan "
        "sudah masuk antrian bengkel.",
    )
    return redirect("kasir_transaksi_detail", pk=transaksi.pk)


@require_POST
@role_required("KASIR")
def tolak_pengajuan(request, pk):
    pengajuan = get_object_or_404(PengajuanServis, pk=pk)
    form = TolakPengajuanForm(request.POST)

    if not form.is_valid():
        for errors in form.errors.values():
            for e in errors:
                messages.error(request, e)
        return redirect("kasir_pengajuan_daftar")

    try:
        pengajuan.tolak(request.user, form.cleaned_data["alasan"])
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        messages.success(
            request,
            f"Pengajuan {pengajuan.kendaraan.no_polisi} ditolak. "
            "Alasannya sudah bisa dibaca pelanggan.",
        )
    return redirect("kasir_pengajuan_daftar")
