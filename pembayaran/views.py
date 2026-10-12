from django.contrib import messages
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


@role_required("KASIR")
def nota_pembayaran(request, pk):
    pembayaran = get_object_or_404(
        Pembayaran.objects.select_related("transaksi__pelanggan__user", "transaksi__kendaraan"), pk=pk
    )
    return render(request, "pembayaran/nota.html", {"pembayaran": pembayaran, "detail": pembayaran.detail()})
