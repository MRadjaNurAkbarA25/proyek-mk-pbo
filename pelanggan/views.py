# pelanggan/views.py
from django.db.models import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import pelanggan_required
from django.db.models import Count
from kendaraan.models import Kendaraan, Mobil, Motor
from .forms import MobilForm, MotorForm, EditProfilPelangganForm
from .beranda import data_beranda

@login_required
@pelanggan_required
def dashboard_pelanggan(request):
    """Beranda (ringkasan): status servis, riwayat terakhir, garasi."""
    profil = request.user.profil_pelanggan
    return render(request, "pelanggan/beranda.html", data_beranda(request.user, profil))


# Formulir per subkelas. Kunci = class model, supaya pemilihan formulir
# mengikuti objek kendaraannya sendiri (Kendaraan.spesifik()), bukan teks tipe.
FORM_PER_JENIS = {Mobil: MobilForm, Motor: MotorForm}


def _jenis_dari_url(tipe):
    """'mobil' -> Mobil. None kalau bukan jenis yang dikenal."""
    for model in Kendaraan.model_subkelas():
        if model.__name__.lower() == tipe:
            return model
    return None


@login_required
@pelanggan_required
def kendaraan_saya(request):
    """Garasi Saya: kartu per kendaraan, dengan jumlah servis masing-masing.

    Satu query: semua kendaraan pelanggan beserta subkelasnya
    (select_related) dan jumlah transaksinya (annotate). Tombol hapus hanya
    untuk kendaraan tanpa riwayat servis, sama dengan aturan
    Kendaraan.alasan_tidak_bisa_dihapus().
    """
    profil = request.user.profil_pelanggan
    daftar = []
    for k in (
        Kendaraan.objects.filter(pelanggan=profil)
        .select_related(*Kendaraan.relasi_subkelas())
        .annotate(jumlah_servis=Count("transaksiservis"))
        .order_by("-pk")
    ):
        s = k.spesifik()
        s.jumlah_servis = k.jumlah_servis
        daftar.append(s)
    return render(request, "pelanggan/kendaraan_saya.html", {"daftar_kendaraan": daftar})


@login_required
@pelanggan_required
def pilih_tipe_kendaraan(request):
    """Langkah 1 dari 2: pilih jenis kendaraan."""
    return render(request, "pelanggan/pilih_tipe_kendaraan.html", {
        "pilihan": [m.__name__.lower() for m in Kendaraan.model_subkelas()],
    })


@login_required
@pelanggan_required
def tambah_kendaraan(request, tipe):
    """Langkah 2 dari 2: isi data kendaraan sesuai jenisnya."""
    model = _jenis_dari_url(tipe)
    if model is None:
        messages.error(request, "Jenis kendaraan tidak dikenal. Pilih Mobil atau Motor.")
        return redirect("pilih_tipe_kendaraan")
    FormClass = FORM_PER_JENIS[model]

    form = FormClass(request.POST or None)
    if request.method == "POST" and form.is_valid():
        kendaraan = form.save(commit=False)
        kendaraan.pelanggan = request.user.profil_pelanggan
        kendaraan.save()
        messages.success(request, f"{kendaraan.get_tipe()} {kendaraan.no_polisi} ditambahkan ke garasi.")
        return redirect("kendaraan_saya")

    return render(request, "pelanggan/form_kendaraan.html", {
        "form": form, "jenis": model.__name__, "ikon": model().ikon, "is_edit": False,
    })


@login_required
@pelanggan_required
def edit_kendaraan(request, pk):
    kendaraan = get_object_or_404(
        Kendaraan.objects.select_related(*Kendaraan.relasi_subkelas()),
        pk=pk, pelanggan=request.user.profil_pelanggan,
    ).spesifik()
    FormClass = FORM_PER_JENIS.get(type(kendaraan))
    if FormClass is None:
        messages.error(request, "Data jenis kendaraan ini tidak lengkap. Hubungi bengkel.")
        return redirect("kendaraan_saya")

    form = FormClass(request.POST or None, instance=kendaraan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Data {kendaraan.no_polisi} diperbarui.")
        return redirect("kendaraan_saya")

    return render(request, "pelanggan/form_kendaraan.html", {
        "form": form, "jenis": kendaraan.get_tipe(), "ikon": kendaraan.ikon, "is_edit": True,
    })

@login_required
@pelanggan_required
def hapus_kendaraan(request, pk):
    profil = request.user.profil_pelanggan
    kendaraan = get_object_or_404(Kendaraan, pk=pk, pelanggan=profil)
    
    if request.method == "POST":
        # Diperiksa di model, bukan cuma lewat ProtectedError: dulu yang
        # tertahan hanya transaksi yang sudah dibayar, sehingga tagihan yang
        # belum dibayar ikut terhapus bersama kendaraannya.
        alasan = kendaraan.alasan_tidak_bisa_dihapus()
        if alasan:
            messages.error(request, alasan)
            return redirect('kendaraan_saya')
        try:
            kendaraan.delete()
        except ProtectedError:
            # Lapis kedua: TransaksiServis.kendaraan memakai on_delete=PROTECT.
            # Hanya terjadi kalau transaksi dibuat persis di antara pemeriksaan
            # di atas dan baris ini.
            messages.error(request, "Kendaraan ini tidak bisa dihapus karena sudah punya riwayat servis.")
            return redirect('kendaraan_saya')
        messages.success(request, "Kendaraan berhasil dihapus.")
    return redirect('kendaraan_saya')

@login_required
@pelanggan_required
def edit_profil(request):
    """URL lama. Profil pelanggan kini digabung ke halaman Profil Saya bersama."""
    return redirect("profil_saya")


