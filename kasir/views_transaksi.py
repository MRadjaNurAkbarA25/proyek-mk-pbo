"""Views Kasir untuk FR-11: buat transaksi servis, daftar, dan detail.

Menggunakan API publik `TransaksiServis` (via `objects.create`) agar logika
`save()` di model (yang membangkitkan kode `TRX-YYYYMMDD-00001`) tetap berjalan.
Status awal otomatis `MENUNGGU` dan tipe `DI_BENGKEL` sehingga transaksi langsung
muncul di antrian bengkel milik mekanik (`/mekanik/antrian/`).
"""

from datetime import datetime, time

from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
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
    "pembayaran",
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


def _batas_hari(teks, akhir=False):
    """'2026-10-15' -> awal atau akhir hari itu pada zona waktu proyek."""
    tanggal = datetime.strptime(teks, "%Y-%m-%d").date()
    return timezone.make_aware(datetime.combine(tanggal, time.max if akhir else time.min))


@role_required("KASIR")
def daftar_transaksi(request):
    """FR-11: daftar transaksi servis dengan pencarian, filter status, dan rentang tanggal."""
    status = (request.GET.get("status") or "").strip().upper()
    cari = (request.GET.get("q") or "").strip()
    tanggal_mulai = (request.GET.get("tanggal_mulai") or "").strip()
    tanggal_selesai = (request.GET.get("tanggal_selesai") or "").strip()

    qs = TransaksiServis.objects.select_related(*RELASI).order_by("-tanggal")

    if status and status in dict(TransaksiServis.STATUS_CHOICES):
        qs = qs.filter(status=status)
    else:
        status = ""

    if cari:
        # Satu kotak untuk nomor polisi, nama/username pelanggan, dan kode transaksi.
        qs = qs.filter(
            Q(kendaraan__no_polisi__icontains=cari)
            | Q(pelanggan__user__first_name__icontains=cari)
            | Q(pelanggan__user__last_name__icontains=cari)
            | Q(pelanggan__user__username__icontains=cari)
            | Q(kode_transaksi__icontains=cari)
        )

    if tanggal_mulai:
        try:
            qs = qs.filter(tanggal__gte=_batas_hari(tanggal_mulai))
        except ValueError:
            tanggal_mulai = ""
    if tanggal_selesai:
        try:
            qs = qs.filter(tanggal__lte=_batas_hari(tanggal_selesai, akhir=True))
        except ValueError:
            tanggal_selesai = ""

    context = {
        "transaksi_list": qs,
        "jumlah_hasil": qs.count(),
        "status_terpilih": status,
        "status_choices": TransaksiServis.STATUS_CHOICES,
        "cari": cari,
        "tanggal_mulai": tanggal_mulai,
        "tanggal_selesai": tanggal_selesai,
        "ada_filter": bool(status or cari or tanggal_mulai or tanggal_selesai),
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
