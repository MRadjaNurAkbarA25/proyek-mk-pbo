"""Lima halaman laporan admin (FR-27 sampai FR-30 + laporan pembelian).

Seluruh perhitungannya ada di hierarki class Laporan (laporan/laporan.py),
sesuai rancangan dokumen bagian 5E. View di sini sengaja dibuat tipis:
tugasnya cuma memeriksa hak akses, memilih class laporan mana yang dipakai,
lalu menyerahkan hasilnya ke template.

Perhatikan kelima fungsi di bawah bentuknya sama persis. Itu memang
polimorfismenya: yang berbeda hanya class yang disebut, karena kelima
class itu menjawab `.konteks()` dengan caranya masing-masing.

Tambahan sejak penyamaan tampilan: tiap view menambahkan dua hal yang murni
urusan TAMPILAN, tanpa mengubah satu pun angka dari class Laporan —
  `periode`  teks rentang tanggal untuk kepala halaman saat dicetak;
  `ringkasan` angka kartu ringkasan di atas tabel.
"""
from datetime import date
from decimal import Decimal

from django.db.models import DecimalField, Sum, Value, prefetch_related_objects
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils.formats import date_format

from accounts.decorators import role_required
from laporan.laporan import (
    LaporanMekanik, LaporanPembelian, LaporanPendapatan, LaporanServis, LaporanStok,
)
from servis.models import TransaksiServis
from sparepart.models import Sparepart

NOL = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))


# --------------------------------------------------------------------- bantuan
def _tanggal_indo(teks):
    """'2026-10-14' -> '14 Okt 2026'. Kosong atau tidak sah -> ''.

    Memakai date_format supaya penulisannya sama dengan filter `date` di
    template (LANGUAGE_CODE = 'id').
    """
    try:
        return date_format(date.fromisoformat(teks), "d M Y")
    except (TypeError, ValueError):
        return ""


def _periode(mulai, selesai):
    """Teks rentang tanggal untuk kepala cetak, mis. '1 Okt 2026 - 26 Okt 2026'."""
    awal, akhir = _tanggal_indo(mulai), _tanggal_indo(selesai)
    if awal and akhir:
        return f"Periode {awal} - {akhir}"
    if awal:
        return f"Periode sejak {awal}"
    if akhir:
        return f"Periode sampai {akhir}"
    return "Periode seluruh data"


def _nilai_transaksi(queryset):
    """Jumlah total_biaya satu queryset transaksi."""
    return queryset.aggregate(total=Coalesce(Sum("total_biaya"), NOL))["total"]


def _ringkasan_servis(konteks):
    """Kartu laporan transaksi: jumlah, selesai, dibatalkan, dan nilai.

    Dasarnya seluruh queryset yang sudah disaring LaporanServis
    (`paginator.object_list`, bukan isi satu halaman), supaya kartunya ikut
    berubah saat filter status atau tanggal dipakai.
    """
    transaksi = konteks["halaman"].paginator.object_list
    return {
        "jumlah": konteks["jumlah_total"],
        "selesai": transaksi.filter(status=TransaksiServis.STATUS_SELESAI).count(),
        "dibatalkan": transaksi.filter(status=TransaksiServis.STATUS_DIBATALKAN).count(),
        "nilai": _nilai_transaksi(transaksi),
    }


# ------------------------------------------------------------------------ view
@role_required("ADMIN")
def laporan_transaksi(request):
    konteks = LaporanServis(request).konteks()
    # Tabel kini menampilkan pelanggan dan nomor polisi; muat sekaligus untuk
    # baris di halaman ini saja, supaya tidak ada dua query tambahan per baris.
    halaman = konteks["halaman"]
    halaman.object_list = list(halaman.object_list)
    prefetch_related_objects(halaman.object_list, "pelanggan__user", "kendaraan")
    konteks["ringkasan"] = _ringkasan_servis(konteks)
    konteks["periode"] = _periode(
        konteks.get("tanggal_mulai"), konteks.get("tanggal_selesai")
    )
    return render(request, "adminpanel/laporan_transaksi.html", konteks)


@role_required("ADMIN")
def laporan_pendapatan(request):
    konteks = LaporanPendapatan(request).konteks()
    konteks["periode"] = _periode(
        konteks.get("tanggal_mulai"), konteks.get("tanggal_selesai")
    )
    return render(request, "adminpanel/laporan_pendapatan.html", konteks)


@role_required("ADMIN")
def laporan_stok(request):
    konteks = LaporanStok(request).konteks()

    # Kartu ringkasan selalu menggambarkan SELURUH gudang, bukan hasil
    # saringan: kalau ikut tersaring, angkanya berubah jadi tidak berguna
    # sebagai gambaran keadaan stok.
    seluruh = list(Sparepart.objects.all())
    konteks["ringkasan"] = {
        "jenis": len(seluruh),
        "minim": sum(1 for s in seluruh if s.status_stok == Sparepart.STOK_MINIM),
        "kosong": sum(1 for s in seluruh if s.status_stok == Sparepart.STOK_KOSONG),
    }
    # Stok adalah keadaan saat ini, bukan kejadian bertanggal.
    konteks["periode"] = "Keadaan stok saat ini"
    return render(request, "adminpanel/laporan_stok.html", konteks)


@role_required("ADMIN")
def laporan_mekanik(request):
    konteks = LaporanMekanik(request).konteks()

    kinerja = konteks["kinerja"]
    konteks["ringkasan"] = {
        "mekanik": len(kinerja),
        "servis": sum(m.servis_selesai for m in kinerja),
        "nilai": sum((m.total_pendapatan for m in kinerja), Decimal("0")),
    }
    konteks["periode"] = _periode(
        konteks.get("tanggal_mulai"), konteks.get("tanggal_selesai")
    )
    return render(request, "adminpanel/laporan_mekanik.html", konteks)


@role_required("ADMIN")
def laporan_pembelian(request):
    konteks = LaporanPembelian(request).konteks()
    konteks["ringkasan"] = {
        "pembelian": konteks["jumlah_total"],
        "pengeluaran": konteks["total_pengeluaran"],
        "supplier": len(konteks["per_supplier"]),
    }
    konteks["periode"] = _periode(
        konteks.get("tanggal_mulai"), konteks.get("tanggal_selesai")
    )
    return render(request, "adminpanel/laporan_pembelian.html", konteks)
