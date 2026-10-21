"""Daftar kendaraan untuk Admin: semua kendaraan milik seluruh pelanggan."""

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from accounts.decorators import role_required
from kendaraan.models import Kendaraan
from servis.models import TransaksiServis

# Nama relasi ke tiap subclass Kendaraan. Ditulis sekali di sini supaya
# menambah jenis kendaraan baru nanti cukup menyentuh satu baris.
SUBKELAS = Kendaraan.SUBKELAS


def _kendaraan_spesifik(kendaraan):
    """Mengembalikan instance subclass-nya agar get_tipe() dan deskripsi_khusus() jalan."""
    for nama in SUBKELAS:
        anak = getattr(kendaraan, nama, None)
        if anak is not None:
            return anak
    return kendaraan


@role_required("ADMIN")
def daftar_kendaraan(request):
    antrian = Q(transaksiservis__status__in=TransaksiServis.STATUS_AKTIF)
    daftar = (
        Kendaraan.objects.select_related("pelanggan__user", *SUBKELAS)
        .annotate(
            jumlah_servis=Count("transaksiservis", distinct=True),
            servis_aktif=Count("transaksiservis", filter=antrian, distinct=True),
        )
        .order_by("no_polisi")
    )

    cari = (request.GET.get("q") or "").strip()
    if cari:
        daftar = daftar.filter(
            Q(no_polisi__icontains=cari)
            | Q(merk__icontains=cari)
            | Q(model_kendaraan__icontains=cari)
            | Q(pelanggan__user__first_name__icontains=cari)
            | Q(pelanggan__user__last_name__icontains=cari)
            | Q(pelanggan__user__username__icontains=cari)
        )

    tipe = (request.GET.get("tipe") or "").strip().lower()
    if tipe in SUBKELAS:
        daftar = daftar.filter(**{f"{tipe}__isnull": False})
    else:
        tipe = ""

    halaman = Paginator(daftar, 25).get_page(request.GET.get("page"))
    # Subclass dilampirkan di sini, bukan di template, supaya template tetap sederhana.
    baris = [(k, _kendaraan_spesifik(k)) for k in halaman]

    kueri = request.GET.copy()
    kueri.pop("page", None)
    return render(request, "adminpanel/kendaraan_daftar.html", {
        "baris": baris,
        "halaman": halaman,
        "kueri": kueri.urlencode(),
        "jumlah_hasil": halaman.paginator.count,
        "cari": cari,
        "tipe": tipe,
        "pilihan_tipe": SUBKELAS,
        "ada_filter": bool(cari or tipe),
    })
