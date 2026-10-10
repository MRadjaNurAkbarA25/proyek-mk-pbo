"""Views Kasir untuk FR-11: buat transaksi servis, daftar, dan detail.

Menggunakan API publik `TransaksiServis` (via `objects.create`) agar logika
`save()` di model (yang membangkitkan kode `TRX-YYYYMMDD-00001`) tetap berjalan.
Status awal otomatis `MENUNGGU` dan tipe `DI_BENGKEL` sehingga transaksi langsung
muncul di antrian bengkel milik mekanik (`/mekanik/antrian/`).
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from servis.models import TransaksiServis

from .forms import BuatTransaksiForm


# Relasi yang di-prefetch untuk tampilan daftar/detail — ikut subclass kendaraan
# supaya `kendaraan_spesifik.get_tipe()` tetap polymorphic.
RELASI = (
    "pelanggan__user",
    "mekanik__user",
    "kendaraan__mobil",
    "kendaraan__motor",
    "kendaraan__truk",
)


@role_required("KASIR")
def buat_transaksi(request):
    """FR-11: Kasir membuat transaksi servis baru (tipe DI_BENGKEL)."""
    if request.method == "POST":
        form = BuatTransaksiForm(request.POST)
        if form.is_valid():
            kendaraan = form.kendaraan
            try:
                transaksi = TransaksiServis.objects.create(
                    pelanggan=kendaraan.pelanggan,
                    kendaraan=kendaraan,
                    keluhan=form.cleaned_data["keluhan"],
                    tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
                    # status otomatis MENUNGGU (default), kode_transaksi dibuat di model.save()
                )
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
                return render(request, "kasir/transaksi_buat.html", {"form": form})

            messages.success(
                request,
                f"Transaksi {transaksi.kode_transaksi} berhasil dibuat dan "
                "sudah masuk ke antrian bengkel.",
            )
            return redirect("kasir_transaksi_detail", pk=transaksi.pk)
    else:
        form = BuatTransaksiForm()

    return render(request, "kasir/transaksi_buat.html", {"form": form})


@role_required("KASIR")
def daftar_transaksi(request):
    """FR-11: daftar transaksi servis dengan filter status."""
    status = (request.GET.get("status") or "").strip().upper()

    qs = TransaksiServis.objects.select_related(*RELASI).order_by("-tanggal")
    if status and status in dict(TransaksiServis.STATUS_CHOICES):
        qs = qs.filter(status=status)

    context = {
        "transaksi_list": qs,
        "status_terpilih": status,
        "status_choices": TransaksiServis.STATUS_CHOICES,
    }
    return render(request, "kasir/transaksi_daftar.html", context)


@role_required("KASIR")
def detail_transaksi(request, pk):
    """FR-11: detail transaksi (read only) — diagnosis, layanan, sparepart, total."""
    transaksi = get_object_or_404(
        TransaksiServis.objects.select_related(*RELASI), pk=pk
    )

    context = {
        "t": transaksi,
        "detail_layanan": transaksi.detail_servis.select_related("jenis_servis"),
        "detail_sparepart": transaksi.detail_sparepart.select_related("sparepart"),
    }
    return render(request, "kasir/transaksi_detail.html", context)
