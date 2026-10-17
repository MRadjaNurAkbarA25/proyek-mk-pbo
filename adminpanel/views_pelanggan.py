from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Pelanggan
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from servis.models import TransaksiServis

from .forms import PelangganCreateForm, PelangganUpdateForm


@role_required("ADMIN")
def daftar_pelanggan(request):
    """Daftar pelanggan dengan pencarian nama/e-mail/username."""
    daftar = Pelanggan.objects.select_related("user").annotate(
        jumlah_transaksi=Count("transaksiservis", distinct=True),
        transaksi_aktif=Count(
            "transaksiservis",
            filter=Q(transaksiservis__status__in=TransaksiServis.STATUS_AKTIF),
            distinct=True,
        ),
    )
    kata_kunci = request.GET.get("q", "").strip()
    if kata_kunci:
        daftar = daftar.filter(
            Q(user__first_name__icontains=kata_kunci)
            | Q(user__last_name__icontains=kata_kunci)
            | Q(user__email__icontains=kata_kunci)
            | Q(user__username__icontains=kata_kunci)
        )
    daftar = daftar.order_by("user__first_name", "user__username")
    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)
    return render(request, "adminpanel/pelanggan_daftar.html", {
        "daftar": halaman,
        "halaman": halaman,
        "kata_kunci": kata_kunci,
    })


@role_required("ADMIN")
def tambah_pelanggan(request):
    form = PelangganCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Pelanggan.objects.create(
                user=user,
            )
        messages.success(request, f"Pelanggan '{user.first_name or user.username}' berhasil ditambahkan.")
        return redirect("kelola_pelanggan")
    return render(request, "adminpanel/pelanggan_form.html", {
        "form": form,
        "judul": "Tambah Pelanggan",
        "mode_tambah": True,
    })


@role_required("ADMIN")
def ubah_pelanggan(request, pk):
    pelanggan = get_object_or_404(Pelanggan.objects.select_related("user"), pk=pk)
    form = PelangganUpdateForm(request.POST or None, instance=pelanggan)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, f"Data pelanggan '{pelanggan.user.first_name or pelanggan.user.username}' berhasil diperbarui.")
        return redirect("kelola_pelanggan")
    return render(request, "adminpanel/pelanggan_form.html", {
        "form": form,
        "judul": f"Ubah Pelanggan: {pelanggan.user.first_name or pelanggan.user.username}",
        "pelanggan": pelanggan,
        "mode_tambah": False,
    })


