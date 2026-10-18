from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from servis.models import TransaksiServis

from .forms import PembayaranForm
from .models import Pembayaran


@role_required("KASIR")
def bayar_transaksi(request, pk):
    transaksi = get_object_or_404(TransaksiServis, pk=pk)
    if request.method != "POST" and hasattr(transaksi, "pembayaran"):
        return redirect("pembayaran_nota", pk=transaksi.pembayaran.pk)
    if transaksi.status != TransaksiServis.STATUS_SELESAI:
        messages.error(request, "Pembayaran hanya dapat diproses untuk transaksi berstatus Selesai.")
        return redirect("kasir_transaksi_detail", pk=transaksi.pk)
    if request.method == "POST":
        form = PembayaranForm(request.POST)
        if form.is_valid():
            try:
                pembayaran = Pembayaran.buat(
                    transaksi, **{k: v for k, v in form.cleaned_data.items() if k != "metode"},
                    metode=form.cleaned_data["metode"],
                )
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            else:
                messages.success(request, "Pembayaran berhasil dicatat.")
                return redirect("pembayaran_nota", pk=pembayaran.pk)
    else:
        form = PembayaranForm()
    return render(request, "pembayaran/bayar.html", {"transaksi": transaksi, "form": form})


@login_required
def nota_pembayaran(request, pk):
    """
    Nota bisa dibuka kasir, admin, dan PELANGGAN PEMILIK transaksinya sendiri.
    Pelanggan lain tetap ditolak (FR-25).
    """
    pembayaran = get_object_or_404(
        Pembayaran.objects.select_related("transaksi__pelanggan__user", "transaksi__kendaraan"), pk=pk
    )
    user = request.user
    pemilik = pembayaran.transaksi.pelanggan and pembayaran.transaksi.pelanggan.user_id == user.id
    boleh = user.is_superuser or user.role in ("KASIR", "ADMIN") or pemilik
    if not boleh:
        messages.error(request, "Anda tidak berhak membuka nota ini.")
        return redirect("dashboard")

    # Pelanggan memakai kerangka halamannya sendiri, bukan navbar kasir.
    # Nota dibuka pelanggan maupun kasir, jadi kerangkanya ikut siapa yang
    # membuka. Kasir dan admin memakai kerangka bersama yang menyesuaikan role.
    base_template = "pelanggan/base.html" if user.role == "PELANGGAN" else "kerangka.html"
    return render(request, "pembayaran/nota.html", {
        "pembayaran": pembayaran,
        "detail": pembayaran.detail(),
        "base_template": base_template,
        "nav": "riwayat_service",
    })
