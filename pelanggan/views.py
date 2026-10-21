# pelanggan/views.py
from django.db.models import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import pelanggan_required
from kendaraan.models import Kendaraan, Mobil, Motor, Truk
from .forms import MobilForm, MotorForm, TrukForm, EditProfilPelangganForm
from .beranda import data_beranda

@login_required
@pelanggan_required
def dashboard_pelanggan(request):
    """Beranda (ringkasan): status servis, riwayat terakhir, garasi."""
    profil = request.user.profil_pelanggan
    return render(request, "pelanggan/beranda.html", data_beranda(request.user, profil))


@login_required
@pelanggan_required
def kendaraan_saya(request):
    """Daftar kendaraan (isi dashboard lama dipindah ke sini)."""
    profil = request.user.profil_pelanggan
    daftar = list(Mobil.objects.filter(pelanggan=profil)) \
           + list(Motor.objects.filter(pelanggan=profil)) \
           + list(Truk.objects.filter(pelanggan=profil))
    return render(request, "pelanggan/dashboard.html", {"profil": profil, "daftar_kendaraan": daftar})  

@login_required
@pelanggan_required
def pilih_tipe_kendaraan(request):
    return render(request, "pelanggan/pilih_tipe_kendaraan.html")

@login_required
@pelanggan_required
def tambah_kendaraan(request, tipe):
    profil = request.user.profil_pelanggan
    
    if tipe == 'mobil': FormClass = MobilForm
    elif tipe == 'motor': FormClass = MotorForm
    elif tipe == 'truk': FormClass = TrukForm
    else:
        messages.error(request, "Tipe kendaraan tidak valid.")
        return redirect('pelanggan_dashboard')

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            kendaraan = form.save(commit=False)
            kendaraan.pelanggan = profil
            kendaraan.save()
            messages.success(request, f"Kendaraan jenis {tipe.capitalize()} berhasil ditambahkan!")
            return redirect('pelanggan_dashboard')
    else:
        form = FormClass()

    return render(request, "pelanggan/form_kendaraan.html", {'form': form, 'tipe': tipe.capitalize(), 'is_edit': False})

@login_required
@pelanggan_required
def edit_kendaraan(request, pk):
    profil = request.user.profil_pelanggan
    kendaraan = None
    FormClass = None
    
    try:
        kendaraan = Mobil.objects.get(pk=pk, pelanggan=profil)
        FormClass = MobilForm
    except Mobil.DoesNotExist:
        try:
            kendaraan = Motor.objects.get(pk=pk, pelanggan=profil)
            FormClass = MotorForm
        except Motor.DoesNotExist:
            try:
                kendaraan = Truk.objects.get(pk=pk, pelanggan=profil)
                FormClass = TrukForm
            except Truk.DoesNotExist:
                messages.error(request, "Kendaraan tidak ditemukan.")
                return redirect('pelanggan_dashboard')

    if request.method == "POST":
        form = FormClass(request.POST, instance=kendaraan)
        if form.is_valid():
            form.save()
            messages.success(request, "Data kendaraan berhasil diperbarui.")
            return redirect('pelanggan_dashboard')
    else:
        form = FormClass(instance=kendaraan)

    return render(request, "pelanggan/form_kendaraan.html", {'form': form, 'tipe': kendaraan.get_tipe(), 'is_edit': True})

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


