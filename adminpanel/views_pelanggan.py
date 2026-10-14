from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Pelanggan
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
    return render(request, "adminpanel/pelanggan_daftar.html", {
        "daftar": daftar,
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
                no_telepon=form.cleaned_data["no_telepon"].strip(),
                alamat=form.cleaned_data["alamat"].strip(),
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


@role_required("ADMIN")
def hapus_pelanggan(request, pk):
    pelanggan = get_object_or_404(Pelanggan.objects.select_related("user"), pk=pk)
    aktif = TransaksiServis.objects.filter(
        pelanggan=pelanggan,
        status__in=TransaksiServis.STATUS_AKTIF,
    ).count()

    if request.method == "POST":
        # Hitung ulang saat konfirmasi untuk mencegah penghapusan jika transaksi
        # aktif muncul setelah halaman konfirmasi dibuka.
        aktif = TransaksiServis.objects.filter(
            pelanggan=pelanggan,
            status__in=TransaksiServis.STATUS_AKTIF,
        ).count()
        if aktif:
            messages.error(
                request,
                f"Pelanggan tidak bisa dihapus karena masih memiliki {aktif} transaksi aktif.",
            )
            return redirect("kelola_pelanggan")

        nama = pelanggan.user.first_name or pelanggan.user.username
        # Relasi pada model saat ini menggunakan CASCADE: transaksi historis dan
        # kendaraan yang terhubung juga akan terhapus bersama akun pelanggan.
        pelanggan.user.delete()
        messages.success(request, f"Pelanggan '{nama}' beserta data terkait berhasil dihapus.")
        return redirect("kelola_pelanggan")

    return render(request, "adminpanel/pelanggan_hapus.html", {
        "pelanggan": pelanggan,
        "aktif": aktif,
        "jumlah_transaksi": TransaksiServis.objects.filter(pelanggan=pelanggan).count(),
    })
