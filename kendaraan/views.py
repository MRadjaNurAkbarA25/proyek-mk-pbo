from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .models import Kendaraan
from .forms import MobilForm, MotorForm, TrukForm
from .models import Kendaraan, Mobil, Motor, Truk


@login_required
def daftar_kendaraan(request):
    pelanggan = request.user.profil_pelanggan

    mobil_list = Mobil.objects.filter(pelanggan=pelanggan)
    motor_list = Motor.objects.filter(pelanggan=pelanggan)
    truk_list = Truk.objects.filter(pelanggan=pelanggan)

    # Gabungkan jadi satu list Python biasa
    kendaraan_list = list(mobil_list) + list(motor_list) + list(truk_list)

    return render(request, "kendaraan/daftar.html", {"kendaraan_list": kendaraan_list})


@login_required
def tambah_kendaraan(request, tipe):
    """tipe: 'mobil', 'motor', atau 'truk' — menentukan form mana yang dipakai."""
    form_class = {"mobil": MobilForm, "motor": MotorForm, "truk": TrukForm}.get(tipe)
    if form_class is None:
        messages.error(request, "Tipe kendaraan tidak dikenali.")
        return redirect("daftar_kendaraan")

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            kendaraan = form.save(commit=False)
            kendaraan.pelanggan = request.user.profil_pelanggan
            kendaraan.save()
            messages.success(request, f"{tipe.capitalize()} berhasil ditambahkan.")
            return redirect("daftar_kendaraan")
    else:
        form = form_class()

    return render(request, "kendaraan/form_kendaraan.html", {"form": form, "tipe": tipe})


@login_required
def cari_kendaraan(request):
    """FR-6: cari kendaraan berdasarkan nomor polisi."""
    query = request.GET.get("q", "")
    hasil = Kendaraan.objects.filter(no_polisi__icontains=query) if query else []
    return render(request, "kendaraan/cari.html", {"hasil": hasil, "query": query})