# mekanik/views_jenis.py -- sisi Admin: kelola Jenis Servis (dipakai Mekanik saat menambah layanan, FR-15)
from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required
from .forms_jenis import JenisServisForm
from .models import JenisServis


@admin_required
def daftar_jenis(request):
    q = request.GET.get("q", "").strip()
    daftar = JenisServis.objects.all().order_by("nama_servis")
    if q:
        daftar = daftar.filter(nama_servis__icontains=q)
    return render(request, "mekanik/jenis_daftar.html", {"daftar": daftar, "q": q})


@admin_required
def tambah_jenis(request):
    form = JenisServisForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        jenis = form.save()
        messages.success(request, f"Jenis servis '{jenis.nama_servis}' berhasil ditambahkan.")
        return redirect("kelola_jenis")
    return render(request, "mekanik/jenis_form.html", {"form": form, "judul": "Tambah Jenis Servis"})


@admin_required
def ubah_jenis(request, pk):
    jenis = get_object_or_404(JenisServis, pk=pk)
    form = JenisServisForm(request.POST or None, instance=jenis)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Jenis servis '{jenis.nama_servis}' diperbarui.")
        return redirect("kelola_jenis")
    return render(request, "mekanik/jenis_form.html", {"form": form, "judul": f"Ubah Jenis Servis: {jenis.nama_servis}"})


@admin_required
def hapus_jenis(request, pk):
    jenis = get_object_or_404(JenisServis, pk=pk)
    dipakai = jenis.detail_transaksi.count()
    if request.method == "POST":
        nama = jenis.nama_servis
        try:
            jenis.delete()
        except ProtectedError:
            # DetailServis.jenis_servis = PROTECT: layanan yang sudah masuk transaksi tidak boleh dihapus
            messages.error(request, f"'{nama}' tidak bisa dihapus karena sudah dipakai di transaksi.")
            return redirect("kelola_jenis")
        messages.success(request, f"Jenis servis '{nama}' berhasil dihapus.")
        return redirect("kelola_jenis")
    return render(request, "mekanik/jenis_hapus.html", {"jenis": jenis, "dipakai": dipakai})
