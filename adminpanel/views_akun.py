"""Kelola Kasir, dan menonaktifkan/mengaktifkan akun kasir dan mekanik.

Akun kasir dan mekanik tidak dihapus, hanya dinonaktifkan: nama mereka
tercatat di riwayat, dan menghapus akun mengosongkan jejak itu. Aturannya
di User.nonaktifkan() / User.aktifkan(); view di sini hanya memanggilnya.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari

from .forms import KasirCreateForm, KasirUpdateForm


def _kasir_atau_404(pk):
    """Halaman kasir hanya boleh menyentuh akun berrole kasir."""
    return get_object_or_404(User, pk=pk, role=User.ROLE_KASIR)


@role_required("ADMIN")
def daftar_kasir(request):
    daftar = User.objects.filter(role=User.ROLE_KASIR).annotate(
        jumlah_pengajuan=Count("pengajuan_servis_diproses", distinct=True),
    )
    kata_kunci = request.GET.get("q", "").strip()
    if kata_kunci:
        daftar = daftar.filter(
            Q(first_name__icontains=kata_kunci)
            | Q(username__icontains=kata_kunci)
            | Q(email__icontains=kata_kunci)
        )
    daftar = daftar.order_by("-is_active", "first_name", "username")
    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)
    return render(request, "adminpanel/kasir_daftar.html", {
        "daftar": halaman, "halaman": halaman, "kata_kunci": kata_kunci,
    })


@role_required("ADMIN")
def tambah_kasir(request):
    form = KasirCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Akun kasir '{user.username}' berhasil dibuat.")
        return redirect("kelola_kasir")
    return render(request, "adminpanel/kasir_form.html", {
        "form": form, "judul": "Tambah Kasir", "mode_tambah": True,
    })


@role_required("ADMIN")
def ubah_kasir(request, pk):
    kasir = _kasir_atau_404(pk)
    form = KasirUpdateForm(request.POST or None, instance=kasir)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Data kasir '{kasir.username}' berhasil diperbarui.")
        return redirect("kelola_kasir")
    return render(request, "adminpanel/kasir_form.html", {
        "form": form, "judul": f"Ubah Kasir: {kasir.username}", "kasir": kasir, "mode_tambah": False,
    })


@role_required("ADMIN")
@require_POST
def ubah_status_akun(request, pk):
    """Nonaktifkan (aktif=0) atau aktifkan (aktif=1) akun kasir atau mekanik."""
    akun = get_object_or_404(User, pk=pk)
    try:
        if request.POST.get("aktif") == "1":
            akun.aktifkan()
            messages.success(request, f"Akun '{akun.username}' diaktifkan kembali.")
        else:
            akun.nonaktifkan()
            messages.success(
                request,
                f"Akun '{akun.username}' dinonaktifkan. Riwayatnya tetap tersimpan.",
            )
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))

    tujuan = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(tujuan, allowed_hosts={request.get_host()}):
        tujuan = "kelola_mekanik" if akun.role == User.ROLE_MEKANIK else "kelola_kasir"
    return redirect(tujuan)
