from datetime import datetime, time
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Mekanik
from pembayaran.models import Pembayaran
from servis.models import TransaksiServis
from sparepart.models import Sparepart

NOL = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))


def _awal_hari(teks):
    """'2026-10-14' -> 14 Okt 00:00 pada zona waktu proyek (Asia/Makassar), bukan datetime naive."""
    tanggal = datetime.strptime(teks, "%Y-%m-%d").date()
    return timezone.make_aware(datetime.combine(tanggal, time.min))


def _akhir_hari(teks):
    """'2026-10-14' -> 14 Okt 23:59:59.999999 pada zona waktu proyek."""
    tanggal = datetime.strptime(teks, "%Y-%m-%d").date()
    return timezone.make_aware(datetime.combine(tanggal, time.max))


def _tanggal_filter(queryset, request):
    tanggal_mulai = request.GET.get("tanggal_mulai", "")
    tanggal_selesai = request.GET.get("tanggal_selesai", "")
    if tanggal_mulai:
        try:
            queryset = queryset.filter(tanggal__gte=_awal_hari(tanggal_mulai))
        except ValueError:
            tanggal_mulai = ""
    if tanggal_selesai:
        try:
            queryset = queryset.filter(tanggal__lte=_akhir_hari(tanggal_selesai))
        except ValueError:
            tanggal_selesai = ""
    return queryset, tanggal_mulai, tanggal_selesai


@role_required("ADMIN")
def laporan_transaksi(request):
    transaksi = TransaksiServis.objects.select_related("mekanik__user").order_by("-tanggal")
    transaksi, tanggal_mulai, tanggal_selesai = _tanggal_filter(transaksi, request)
    status = request.GET.get("status", "")
    if status:
        transaksi = transaksi.filter(status=status)

    halaman = Paginator(transaksi, 25).get_page(request.GET.get("page"))
    kueri = request.GET.copy()
    kueri.pop("page", None)
    return render(request, "adminpanel/laporan_transaksi.html", {
        "transaksi": halaman, "halaman": halaman, "kueri": kueri.urlencode(),
        "jumlah_total": halaman.paginator.count,
        "status": status, "status_choices": TransaksiServis.STATUS_CHOICES,
        "tanggal_mulai": tanggal_mulai, "tanggal_selesai": tanggal_selesai,
    })


@role_required("ADMIN")
def laporan_pendapatan(request):
    transaksi, tanggal_mulai, tanggal_selesai = _tanggal_filter(
        TransaksiServis.objects.filter(status=TransaksiServis.STATUS_SELESAI), request
    )
    nilai_servis = transaksi.aggregate(total=Coalesce(Sum("total_biaya"), NOL))["total"]

    per_hari = transaksi.annotate(periode=TruncDate("tanggal")).values("periode").annotate(
        total=Sum("total_biaya"), jumlah=Count("id")).order_by("-periode")
    per_bulan = transaksi.annotate(periode=TruncMonth("tanggal")).values("periode").annotate(
        total=Sum("total_biaya"), jumlah=Count("id")).order_by("-periode")

    # Pendapatan yang benar-benar diterima diambil dari modul Pembayaran (FR-28),
    # bukan dari total_biaya transaksi yang statusnya Selesai tapi belum tentu dibayar.
    pembayaran = Pembayaran.objects.filter(transaksi__in=transaksi)
    total_dibayar = pembayaran.aggregate(total=Coalesce(Sum("total"), NOL))["total"]
    nama_metode = dict(Pembayaran.METODE_CHOICES)
    per_metode = [
        {"metode": nama_metode.get(baris["metode"], baris["metode"]),
         "jumlah": baris["jumlah"], "total": baris["total"]}
        for baris in pembayaran.values("metode").annotate(
            total=Sum("total"), jumlah=Count("id")).order_by("-total")
    ]

    jumlah_belum_dibayar = transaksi.filter(pembayaran__isnull=True).count()
    return render(request, "adminpanel/laporan_pendapatan.html", {
        "total": nilai_servis,            # nilai seluruh servis berstatus Selesai
        "total_dibayar": total_dibayar,   # uang yang benar-benar sudah masuk
        "total_piutang": nilai_servis - total_dibayar,
        "jumlah_belum_dibayar": jumlah_belum_dibayar,
        "per_hari": per_hari, "per_bulan": per_bulan, "per_metode": per_metode,
        "tanggal_mulai": tanggal_mulai, "tanggal_selesai": tanggal_selesai,
    })


@role_required("ADMIN")
def laporan_stok(request):
    spareparts = Sparepart.objects.order_by("nama")
    hanya_kritis = request.GET.get("kritis") == "1"
    if hanya_kritis:
        spareparts = [s for s in spareparts if s.is_stok_kritis]
    return render(request, "adminpanel/laporan_stok.html", {
        "spareparts": spareparts, "hanya_kritis": hanya_kritis,
    })


@role_required("ADMIN")
def laporan_mekanik(request):
    transaksi, tanggal_mulai, tanggal_selesai = _tanggal_filter(
        TransaksiServis.objects.filter(status=TransaksiServis.STATUS_SELESAI), request
    )
    # Semua mekanik ikut tampil, termasuk yang belum punya servis selesai (jumlah 0).
    selesai = Q(transaksi_servis__in=transaksi)
    kinerja = Mekanik.objects.select_related("user").annotate(
        servis_selesai=Count("transaksi_servis", filter=selesai),
        total_pendapatan=Coalesce(Sum("transaksi_servis__total_biaya", filter=selesai), NOL),
    ).order_by("-servis_selesai", "user__username")

    tanpa_mekanik = transaksi.filter(mekanik__isnull=True).aggregate(
        jumlah=Count("id"), total=Coalesce(Sum("total_biaya"), NOL))
    return render(request, "adminpanel/laporan_mekanik.html", {
        "kinerja": kinerja, "tanpa_mekanik": tanpa_mekanik,
        "tanggal_mulai": tanggal_mulai, "tanggal_selesai": tanggal_selesai,
    })
