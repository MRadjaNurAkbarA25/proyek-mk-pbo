from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Mekanik, Pelanggan
from pembayaran.models import Pembayaran
from servis.models import TransaksiServis
from sparepart.models import Sparepart

# Sum() mengembalikan None kalau tidak ada baris; Coalesce membuatnya 0 supaya
# template tidak perlu menangani nilai kosong.
NOL = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))


def _ringkasan():
    """Angka-angka untuk kartu ringkasan di dashboard admin.

    Dihitung lewat agregasi database (Count/Sum), bukan dengan mengambil semua
    baris lalu menghitung di Python, supaya tetap ringan saat data bertambah.
    """
    sekarang = timezone.localtime()
    awal_bulan = sekarang.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    transaksi = TransaksiServis.objects.aggregate(
        aktif=Count("pk", filter=Q(status__in=TransaksiServis.STATUS_AKTIF)),
        selesai_bulan_ini=Count(
            "pk",
            filter=Q(status=TransaksiServis.STATUS_SELESAI, tanggal__gte=awal_bulan),
        ),
        menunggu_konfirmasi=Count(
            "pk", filter=Q(status=TransaksiServis.STATUS_MENUNGGU_KONFIRMASI)
        ),
    )

    pendapatan = Pembayaran.objects.filter(tanggal__gte=awal_bulan).aggregate(
        total=Coalesce(Sum("total"), NOL),
        jumlah=Count("pk"),
    )

    mekanik = Mekanik.objects.aggregate(
        total=Count("pk"),
        tersedia=Count("pk", filter=Q(status=Mekanik.STATUS_TERSEDIA)),
        cuti=Count("pk", filter=Q(status=Mekanik.STATUS_CUTI)),
    )

    sparepart = Sparepart.objects.aggregate(
        total=Count("pk"),
        kritis=Count("pk", filter=Q(stok__lte=F("stok_minimum"))),
        kosong=Count("pk", filter=Q(stok__lte=0)),
    )

    return {
        "transaksi_aktif": transaksi["aktif"],
        "transaksi_selesai_bulan": transaksi["selesai_bulan_ini"],
        "transaksi_menunggu_konfirmasi": transaksi["menunggu_konfirmasi"],
        "pendapatan_bulan": pendapatan["total"],
        "pembayaran_bulan": pendapatan["jumlah"],
        "mekanik_total": mekanik["total"],
        "mekanik_tersedia": mekanik["tersedia"],
        "mekanik_cuti": mekanik["cuti"],
        "sparepart_total": sparepart["total"],
        "sparepart_kritis": sparepart["kritis"],
        "sparepart_kosong": sparepart["kosong"],
        "jumlah_pelanggan": Pelanggan.objects.count(),
        "nama_bulan": awal_bulan,
    }


@role_required("ADMIN")
def dashboard_admin(request):
    context = {"user": request.user}
    context.update(_ringkasan())
    context["servis_terbaru"] = (
        TransaksiServis.objects
        .select_related("pelanggan__user", "mekanik__user", "kendaraan")
        .order_by("-tanggal")[:5]
    )
    return render(request, "adminpanel/dashboard.html", context)
