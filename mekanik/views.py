# mekanik/views.py  -- sisi Mekanik
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.views.decorators.http import require_POST

from accounts.models import Mekanik
from servis.models import TransaksiServis as T

from .decorators import mekanik_required
from .forms import (
    DiagnosisForm, StatusKetersediaanForm, TambahLayananForm, TambahSparepartForm,
)

# Subclass kendaraan ikut diambil agar get_tipe()/deskripsi_khusus() polimorfis.
RELASI = ("pelanggan__user", "mekanik__user", "kendaraan__mobil", "kendaraan__motor", "kendaraan__truk")
STATUS_PEKERJAAN_SAYA = [T.STATUS_MENUNGGU, T.STATUS_MENUNGGU_KONFIRMASI, T.STATUS_DIKERJAKAN]


def _antrian_bengkel():
    return T.objects.filter(mekanik__isnull=True, tipe_layanan=T.TIPE_DI_BENGKEL, status=T.STATUS_MENUNGGU)


def _pesan_form_error(request, form):
    for errors in form.errors.values():
        for e in errors:
            messages.error(request, e)


def _eksekusi(request, transaksi, aksi, pesan_sukses):
    """Jalankan satu aksi model; ValidationError dari aturan bisnis ditampilkan sebagai pesan."""
    try:
        aksi()
        messages.success(request, pesan_sukses)
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    return redirect("mekanik_detail", pk=transaksi.pk)


def _transaksi_saya(request, pk):
    return get_object_or_404(T, pk=pk, mekanik=request.mekanik)


@mekanik_required
def dashboard_mekanik(request):
    mekanik = request.mekanik
    mekanik.perbarui_status_otomatis()
    saya = T.objects.filter(mekanik=mekanik)
    context = {
        "mekanik": mekanik,
        "jumlah_servis": mekanik.jumlah_servis,
        "sibuk": mekanik.punya_pekerjaan_berjalan(),
        "jml_permintaan": saya.filter(status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK).count(),
        "jml_aktif": saya.filter(status__in=STATUS_PEKERJAAN_SAYA).count(),
        "jml_antrian": _antrian_bengkel().count(),
        "form_status": StatusKetersediaanForm(
            initial={"status": Mekanik.STATUS_CUTI if mekanik.status == Mekanik.STATUS_CUTI else Mekanik.STATUS_TERSEDIA}
        ),
    }
    return render(request, "mekanik/dashboard.html", context)


@mekanik_required
@require_POST
def ubah_ketersediaan(request):
    """FR-9."""
    form = StatusKetersediaanForm(request.POST)
    if not form.is_valid():
        _pesan_form_error(request, form)
    else:
        try:
            request.mekanik.ubah_ketersediaan(form.cleaned_data["status"])
            messages.success(request, f"Status diubah menjadi {request.mekanik.get_status_display()}.")
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
    return redirect("mekanik_dashboard")


@mekanik_required
def antrian_servis(request):
    """FR-10: antrian kerja mekanik."""
    mekanik = request.mekanik
    mekanik.perbarui_status_otomatis()
    semua = T.objects.select_related(*RELASI)
    context = {
        "permintaan_home_service": semua.filter(
            mekanik=mekanik, status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK).order_by("tanggal"),
        "pekerjaan_saya": semua.filter(mekanik=mekanik, status__in=STATUS_PEKERJAAN_SAYA).order_by("tanggal"),
        "antrian_bengkel": semua.filter(
            mekanik__isnull=True, tipe_layanan=T.TIPE_DI_BENGKEL, status=T.STATUS_MENUNGGU).order_by("tanggal"),
        "riwayat": semua.filter(
            mekanik=mekanik, status__in=[T.STATUS_SELESAI, T.STATUS_DIBATALKAN]).order_by("-tanggal")[:10],
    }
    return render(request, "mekanik/antrian.html", context)


@mekanik_required
def detail_servis(request, pk):
    # Boleh dilihat: milik saya, atau antrian bengkel yang belum diambil siapa pun.
    transaksi = get_object_or_404(
        T.objects.select_related(*RELASI), Q(mekanik=request.mekanik) | Q(mekanik__isnull=True), pk=pk,
    )
    milik_saya = transaksi.mekanik_id == request.mekanik.pk
    context = {
        "t": transaksi,
        "milik_saya": milik_saya,
        "bisa_diambil": (not transaksi.mekanik_id and transaksi.status == T.STATUS_MENUNGGU
                         and transaksi.tipe_layanan == T.TIPE_DI_BENGKEL),
        "menunggu_respon_saya": milik_saya and transaksi.status == T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
        "form_diagnosis": DiagnosisForm(instance=transaksi),
        "form_layanan": TambahLayananForm(),
        "form_sparepart": TambahSparepartForm(),
        "detail_layanan": transaksi.detail_servis.select_related("jenis_servis"),
        "detail_sparepart": transaksi.detail_sparepart.select_related("sparepart"),
    }
    return render(request, "mekanik/detail.html", context)


@mekanik_required
@require_POST
def ambil_pekerjaan(request, pk):
    transaksi = get_object_or_404(T, pk=pk)
    return _eksekusi(request, transaksi, lambda: transaksi.ambil_oleh(request.mekanik),
                     "Pekerjaan berhasil Anda ambil.")


@mekanik_required
@require_POST
def terima_home_service(request, pk):
    transaksi = _transaksi_saya(request, pk)
    return _eksekusi(request, transaksi, transaksi.terima_home_service, "Home service diterima.")


@mekanik_required
@require_POST
def tolak_home_service(request, pk):
    transaksi = _transaksi_saya(request, pk)
    return _eksekusi(request, transaksi, transaksi.tolak_home_service, "Home service ditolak.")


@mekanik_required
@require_POST
def input_diagnosis(request, pk):
    """FR-12."""
    transaksi = _transaksi_saya(request, pk)
    form = DiagnosisForm(request.POST)
    if not form.is_valid():
        _pesan_form_error(request, form)
        return redirect("mekanik_detail", pk=pk)
    return _eksekusi(
        request, transaksi,
        lambda: transaksi.input_diagnosis(form.cleaned_data["diagnosis"], form.cleaned_data["rekomendasi_perbaikan"]),
        "Diagnosis tersimpan. Menunggu konfirmasi pelanggan.",
    )


@mekanik_required
@require_POST
def tambah_layanan(request, pk):
    """FR-15, FR-16."""
    transaksi = _transaksi_saya(request, pk)
    form = TambahLayananForm(request.POST)
    if not form.is_valid():
        _pesan_form_error(request, form)
        return redirect("mekanik_detail", pk=pk)
    return _eksekusi(
        request, transaksi,
        lambda: transaksi.tambah_layanan(form.cleaned_data["jenis_servis"], form.cleaned_data["jumlah"]),
        "Layanan ditambahkan.",
    )


@mekanik_required
@require_POST
def tambah_sparepart(request, pk):
    """FR-15, FR-22 (stok berkurang otomatis), FR-23 (peringatan stok minimum)."""
    transaksi = _transaksi_saya(request, pk)
    form = TambahSparepartForm(request.POST)
    if not form.is_valid():
        _pesan_form_error(request, form)
        return redirect("mekanik_detail", pk=pk)
    sparepart = form.cleaned_data["sparepart"]
    response = _eksekusi(
        request, transaksi,
        lambda: transaksi.tambah_sparepart(sparepart, form.cleaned_data["jumlah"]),
        "Sparepart dicatat, stok berkurang otomatis.",
    )
    sparepart.refresh_from_db()
    if sparepart.is_stok_kritis:
        messages.warning(request, f"Peringatan: stok {sparepart.nama} tinggal {sparepart.stok} (minimum {sparepart.stok_minimum}).")
    return response


@mekanik_required
@require_POST
def selesaikan_servis(request, pk):
    transaksi = _transaksi_saya(request, pk)
    return _eksekusi(request, transaksi, transaksi.selesaikan, "Servis ditandai selesai.")


@mekanik_required
@require_POST
def lanjut_di_bengkel(request, pk):
    """FR-20."""
    transaksi = _transaksi_saya(request, pk)
    return _eksekusi(request, transaksi, transaksi.lanjutkan_di_bengkel,
                     "Transaksi diubah menjadi servis lanjutan di bengkel.")
