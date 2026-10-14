from datetime import datetime, time
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render

from servis.models import TransaksiServis
from sparepart.models import Sparepart


def _is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.role == "ADMIN")


def admin_required(view):
    return login_required(user_passes_test(_is_admin, login_url="login")(view))


def _tanggal_filter(queryset, request):
    tanggal_mulai = request.GET.get("tanggal_mulai", "")
    tanggal_selesai = request.GET.get("tanggal_selesai", "")
    if tanggal_mulai:
        try:
            queryset = queryset.filter(tanggal__gte=datetime.combine(datetime.strptime(tanggal_mulai, "%Y-%m-%d").date(), time.min))
        except ValueError:
            tanggal_mulai = ""
    if tanggal_selesai:
        try:
            queryset = queryset.filter(tanggal__lt=datetime.combine(datetime.strptime(tanggal_selesai, "%Y-%m-%d").date(), time.max))
        except ValueError:
            tanggal_selesai = ""
    return queryset, tanggal_mulai, tanggal_selesai


@admin_required
def laporan_transaksi(request):
    transaksi = TransaksiServis.objects.select_related("mekanik").order_by("-tanggal")
    transaksi, tanggal_mulai, tanggal_selesai = _tanggal_filter(transaksi, request)
    status = request.GET.get("status", "")
    if status:
        transaksi = transaksi.filter(status=status)
    return render(request, "adminpanel/laporan_transaksi.html", {
        "transaksi": transaksi, "status": status, "status_choices": TransaksiServis.STATUS_CHOICES,
        "tanggal_mulai": tanggal_mulai, "tanggal_selesai": tanggal_selesai,
    })


@admin_required
def laporan_pendapatan(request):
    transaksi, tanggal_mulai, tanggal_selesai = _tanggal_filter(
        TransaksiServis.objects.filter(status=TransaksiServis.STATUS_SELESAI), request
    )
    total = transaksi.aggregate(total=Sum("total_biaya"))["total"] or Decimal("0")
    per_hari = transaksi.annotate(periode=TruncDate("tanggal")).values("periode").annotate(total=Sum("total_biaya"), jumlah=Count("id")).order_by("-periode")
    per_bulan = transaksi.annotate(periode=TruncMonth("tanggal")).values("periode").annotate(total=Sum("total_biaya"), jumlah=Count("id")).order_by("-periode")
    per_metode = [{"metode": "Belum tercatat", "total": total, "jumlah": transaksi.count()}]
    return render(request, "adminpanel/laporan_pendapatan.html", {
        "total": total, "per_hari": per_hari, "per_bulan": per_bulan, "per_metode": per_metode,
        "tanggal_mulai": tanggal_mulai, "tanggal_selesai": tanggal_selesai,
    })


@admin_required
def laporan_stok(request):
    return render(request, "adminpanel/laporan_stok.html", {"spareparts": Sparepart.objects.order_by("nama")})


@admin_required
def laporan_mekanik(request):
    transaksi, tanggal_mulai, tanggal_selesai = _tanggal_filter(
        TransaksiServis.objects.filter(status=TransaksiServis.STATUS_SELESAI), request
    )
    kinerja = transaksi.values("mekanik__user__username", "mekanik__spesialisasi").annotate(
        jumlah_servis=Count("id"), total_pendapatan=Sum("total_biaya")
    ).order_by("mekanik__user__username")
    return render(request, "adminpanel/laporan_mekanik.html", {
        "kinerja": kinerja, "tanggal_mulai": tanggal_mulai, "tanggal_selesai": tanggal_selesai,
    })
