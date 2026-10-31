"""Views Kasir FR-11: buat transaksi servis (lewat TransaksiServis.buka()), daftar, dan detail."""

from datetime import datetime, time

from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from kendaraan.models import Kendaraan
from mekanik.views import _antrian_bengkel
from pembayaran.models import BuktiPembayaran
from servis.models import TransaksiServis

from .forms import BuatTransaksiForm


# Relasi yang di-prefetch untuk tampilan daftar/detail — ikut subclass kendaraan
# supaya `kendaraan_spesifik.get_tipe()` tetap polymorphic.
RELASI = (
    "pelanggan__user",
    "mekanik__user",
    "pembayaran",
    *Kendaraan.relasi_subkelas("kendaraan__"),
)


def untuk_tabel(qs):
    """Queryset transaksi + `ada_bukti_menunggu` untuk badge status dan pembayaran (kasir/_badge_bayar.html)."""
    return TransaksiServis.dengan_status_bayar(qs).select_related(*RELASI)


@role_required("KASIR")
def buat_transaksi(request):
    """FR-11: Kasir membuat transaksi servis baru (tipe DI_BENGKEL)."""
    if request.method == "POST":
        form = BuatTransaksiForm(request.POST)
        if form.is_valid():
            kendaraan = form.kendaraan
            try:
                # buka(), bukan objects.create(): menolak kendaraan yang masih
                # punya pekerjaan atau pengajuan berjalan, dan menulis baris
                # pertama linimasa pelanggan (FR-32).
                transaksi = TransaksiServis.buka(
                    keterangan="Kendaraan diterima di bengkel dan didaftarkan kasir.",
                    oleh=request.user,
                    pelanggan=kendaraan.pelanggan,
                    kendaraan=kendaraan,
                    keluhan=form.cleaned_data["keluhan"],
                    tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
                    # status otomatis MENUNGGU (default), kode_transaksi dibuat di model.save()
                )
            except ValidationError as e:
                # Ditempel di kolom nomor polisi, tepat di bawah kendaraan
                # yang ditolak, supaya kasir langsung tahu sebabnya.
                form.add_error("no_polisi", " ".join(e.messages))
                return _halaman_buat(request, form)

            messages.success(
                request,
                f"Transaksi {transaksi.kode_transaksi} berhasil dibuat dan "
                "sudah masuk ke antrian bengkel.",
            )
            return redirect("kasir_transaksi_detail", pk=transaksi.pk)
    else:
        # Dari tombol "Buat transaksi" di hasil Cari Kendaraan.
        form = BuatTransaksiForm(initial={"no_polisi": request.GET.get("no_polisi", "").strip()[:15]})

    return _halaman_buat(request, form)


def _halaman_buat(request, form):
    # Antrian yang sama persis dengan yang dilihat mekanik, untuk panel kanan.
    return render(request, "kasir/transaksi_buat.html", {
        "form": form, "jumlah_antrian": _antrian_bengkel().count(),
    })


def _batas_hari(teks, akhir=False):
    """'2026-10-15' -> awal atau akhir hari itu pada zona waktu proyek."""
    tanggal = datetime.strptime(teks, "%Y-%m-%d").date()
    return timezone.make_aware(datetime.combine(tanggal, time.max if akhir else time.min))


@role_required("KASIR")
def daftar_transaksi(request):
    """FR-11: daftar transaksi servis dengan pencarian, filter status, dan rentang tanggal."""
    # FR-31 C: sapu transaksi kedaluwarsa dulu (juga dipanggil dari sisi pelanggan).
    TransaksiServis.sapu_kedatangan_lewat()

    status = (request.GET.get("status") or "").strip().upper()
    cari = (request.GET.get("q") or "").strip()
    tanggal_mulai = (request.GET.get("tanggal_mulai") or "").strip()
    tanggal_selesai = (request.GET.get("tanggal_selesai") or "").strip()
    perlu = request.GET.get("perlu") == "1"

    qs = untuk_tabel(TransaksiServis.objects.order_by("-tanggal"))
    if perlu:
        # Baris yang sama persis dengan badge menu (TransaksiServis.perlu_tindakan_kasir).
        qs = qs.filter(pk__in=TransaksiServis.perlu_tindakan_kasir().values("pk"))

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

    # Jumlah dihitung dari paginator supaya tidak ada query COUNT kedua.
    halaman = halaman_dari(request, qs, PER_HALAMAN_TABEL)

    context = {
        "transaksi_list": halaman,
        "halaman": halaman,
        "jumlah_hasil": halaman.paginator.count,
        "status_terpilih": status,
        "status_choices": TransaksiServis.STATUS_CHOICES,
        "cari": cari,
        "tanggal_mulai": tanggal_mulai,
        "tanggal_selesai": tanggal_selesai,
        "perlu": perlu,
        "ada_filter": bool(status or cari or tanggal_mulai or tanggal_selesai or perlu),
    }
    return render(request, "kasir/transaksi_daftar.html", context)


@require_POST
@role_required("KASIR")
def tandai_kendaraan_tiba(request, pk):
    """FR-31: kasir menandai kendaraan tiba; baru setelah ini masuk antrian mekanik."""
    transaksi = get_object_or_404(TransaksiServis, pk=pk)
    try:
        transaksi.tandai_kendaraan_tiba()
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        messages.success(
            request,
            f"Kendaraan {transaksi.kendaraan.no_polisi} ditandai sudah tiba. "
            "Transaksi ini sekarang masuk antrian bengkel.",
        )
    return redirect("kasir_transaksi_detail", pk=transaksi.pk)


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
        # FR-32: linimasa yang sama dengan yang dibaca pelanggan, supaya
        # kasir yang ditelepon bisa menjawab "motor saya sampai mana".
        "pembaruan": transaksi.pembaruan.select_related("oleh"),
        "bukti_menunggu": BuktiPembayaran.menunggu_untuk(transaksi),
    }
    return render(request, "kasir/transaksi_detail.html", context)
