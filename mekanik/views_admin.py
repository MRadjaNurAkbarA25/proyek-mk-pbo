# mekanik/views_admin.py  -- sisi Admin: kelola data mekanik (FR-8, FR-9)
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Mekanik
from servis.models import TransaksiServis as T

from .decorators import admin_required
from .forms import MekanikCreateForm, MekanikUpdateForm


@admin_required
def daftar_mekanik(request):
    daftar = Mekanik.objects.select_related("user").annotate(
        total_selesai=Count("transaksi_servis", filter=Q(transaksi_servis__status=T.STATUS_SELESAI))
    ).order_by("user__username")
    return render(request, "mekanik/kelola_daftar.html", {"daftar": daftar})


@admin_required
def tambah_mekanik(request):
    form = MekanikCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Mekanik '{user.username}' berhasil ditambahkan.")
        return redirect("kelola_mekanik")
    return render(request, "mekanik/kelola_form.html", {"form": form, "judul": "Tambah Mekanik"})


@admin_required
def ubah_mekanik(request, pk):
    mekanik = get_object_or_404(Mekanik.objects.select_related("user"), pk=pk)
    form = MekanikUpdateForm(request.POST or None, instance=mekanik)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Data mekanik '{mekanik.user.username}' diperbarui.")
        return redirect("kelola_mekanik")
    return render(request, "mekanik/kelola_form.html",
                  {"form": form, "judul": f"Ubah Mekanik: {mekanik.user.username}", "mekanik": mekanik})


@admin_required
def hapus_mekanik(request, pk):
    mekanik = get_object_or_404(Mekanik.objects.select_related("user"), pk=pk)
    aktif = mekanik.transaksi_servis.filter(status__in=T.STATUS_AKTIF).count()
    if request.method == "POST":
        if aktif:
            messages.error(request, f"Tidak bisa dihapus: masih ada {aktif} transaksi aktif.")
            return redirect("kelola_mekanik")
        nama = mekanik.user.username
        mekanik.user.delete()  # profil Mekanik ikut terhapus (CASCADE)
        messages.success(request, f"Mekanik '{nama}' berhasil dihapus.")
        return redirect("kelola_mekanik")
    return render(request, "mekanik/kelola_hapus.html", {"mekanik": mekanik, "aktif": aktif})
