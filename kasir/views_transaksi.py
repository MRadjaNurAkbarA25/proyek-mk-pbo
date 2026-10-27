"""Views Kasir untuk FR-11: buat transaksi servis, daftar, dan detail.

Transaksi dibuat lewat `TransaksiServis.buka()`, pintu yang sama dengan
pengajuan dan home service: aturan satu kendaraan satu pekerjaan diperiksa
di sana, baris pertama linimasa ditulis di sana, dan `save()` di model tetap
membangkitkan kode `TRX-YYYYMMDD-00001`.
Status awal otomatis `MENUNGGU` dan tipe `DI_BENGKEL` sehingga transaksi langsung
muncul di antrian bengkel milik mekanik (`/mekanik/antrian/`).
"""

from datetime import datetime, time

from django.contrib import messages
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from kendaraan.models import Kendaraan
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
    """Queryset transaksi + `ada_bukti_menunggu` untuk badge pembayaran (kasir/_badge_bayar.html)."""
    menunggu = BuktiPembayaran.objects.filter(
        transaksi=OuterRef("pk"), status=BuktiPembayaran.STATUS_MENUNGGU)
    return qs.select_related(*RELASI).annotate(ada_bukti_menunggu=Exists(menunggu))


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
                return render(request, "kasir/transaksi_buat.html", {"form": form})

            messages.success(
                request,
                f"Transaksi {transaksi.kode_transaksi} berhasil dibuat dan "
                "sudah masuk ke antrian bengkel.",
            )
            return redirect("kasir_transaksi_detail", pk=transaksi.pk)
    else:
        # Dari tombol "Buat transaksi" di hasil Cari Kendaraan.
        form = BuatTransaksiForm(initial={"no_polisi": request.GET.get("no_polisi", "").strip()[:15]})

    return render(request, "kasir/transaksi_buat.html", {"form": form})


def _batas_hari(teks, akhir=False):
    """'2026-10-15' -> awal atau akhir hari itu pada zona waktu proyek."""
    tanggal = datetime.strptime(teks, "%Y-%m-%d").date()
    return timezone.make_aware(datetime.combine(tanggal, time.max if akhir else time.min))


@role_required("KASIR")
def daftar_transaksi(request):
    """FR-11: daftar transaksi servis dengan pencarian, filter status, dan rentang tanggal."""
    # FR-31 C: batalkan dulu transaksi yang kendaraannya tidak kunjung
    # datang, supaya daftar di bawah ini tidak menampilkan transaksi yang
    # sebenarnya sudah kedaluwarsa. Dipanggil dari sisi kasir MAUPUN
    # pelanggan: kalau hanya kasir, pelanggan bisa melihat transaksi yang
    # seharusnya sudah batal selama kasirnya belum membuka halaman.
    TransaksiServis.sapu_kedatangan_lewat()

    status = (request.GET.get("status") or "").strip().upper()
    cari = (request.GET.get("q") or "").strip()
    tanggal_mulai = (request.GET.get("tanggal_mulai") or "").strip()
    tanggal_selesai = (request.GET.get("tanggal_selesai") or "").strip()

    qs = untuk_tabel(TransaksiServis.objects.order_by("-tanggal"))

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
        "ada_filter": bool(status or cari or tanggal_mulai or tanggal_selesai),
    }
    return render(request, "kasir/transaksi_daftar.html", context)


@require_POST
@role_required("KASIR")
def tandai_kendaraan_tiba(request, pk):
    """FR-31: kasir menandai kendaraan sudah sampai di bengkel.

    Baru setelah ini transaksinya muncul di antrian mekanik. Dipakai untuk
    transaksi hasil pengajuan pelanggan, yang disetujui saat kendaraannya
    masih di rumah.
    """
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
