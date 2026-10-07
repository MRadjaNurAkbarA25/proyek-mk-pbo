# pelanggan/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .decorators import pelanggan_required
from kendaraan.models import Kendaraan, Mobil, Motor, Truk
from .forms import MobilForm, MotorForm, TrukForm

@login_required
@pelanggan_required
def dashboard_pelanggan(request):
    profil = request.user.profil_pelanggan
    
    # Query dari masing-masing subclass agar mendapat instance yang benar
    mobils = Mobil.objects.filter(pelanggan=profil)
    motors = Motor.objects.filter(pelanggan=profil)
    trucks = Truk.objects.filter(pelanggan=profil)
    
    # Gabungkan semua kendaraan (sudah dalam bentuk instance subclass yang benar)
    daftar_kendaraan = list(mobils) + list(motors) + list(trucks)
    
    context = {
        "user": request.user,
        "profil": profil,
        "daftar_kendaraan": daftar_kendaraan,
    }
    return render(request, "pelanggan/dashboard.html", context)

@login_required
@pelanggan_required
def pilih_tipe_kendaraan(request):
    return render(request, "pelanggan/pilih_tipe_kendaraan.html")

@login_required
@pelanggan_required
def tambah_kendaraan(request, tipe):
    profil = request.user.profil_pelanggan
    
    if tipe == 'mobil':
        FormClass = MobilForm
    elif tipe == 'motor':
        FormClass = MotorForm
    elif tipe == 'truk':
        FormClass = TrukForm
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

    context = {
        'form': form,
        'tipe': tipe.capitalize(),
        'is_edit': False
    }
    return render(request, "pelanggan/form_kendaraan.html", context)

@login_required
@pelanggan_required
def edit_kendaraan(request, pk):
    profil = request.user.profil_pelanggan
    
    # Coba ambil dari masing-masing subclass
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

    context = {
        'form': form,
        'tipe': kendaraan.get_tipe(),
        'kendaraan': kendaraan,
        'is_edit': True
    }
    return render(request, "pelanggan/form_kendaraan.html", context)

@login_required
@pelanggan_required
def hapus_kendaraan(request, pk):
    profil = request.user.profil_pelanggan
    
    # Hapus dari class induk (akan cascade ke subclass)
    kendaraan = get_object_or_404(Kendaraan, pk=pk, pelanggan=profil)
    
    if request.method == "POST":
        kendaraan.delete()
        messages.success(request, "Kendaraan berhasil dihapus.")
    else:
        messages.error(request, "Metode tidak valid untuk menghapus data.")
        
    return redirect('pelanggan_dashboard')