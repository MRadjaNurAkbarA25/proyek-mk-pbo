import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import mekanik_required, pelanggan_required, role_required
from servis.models import TransaksiServis

from .forms import BuktiPembayaranForm, CashForm, TolakBuktiForm
from .models import BuktiPembayaran, Pembayaran


@role_required("KASIR")
def bayar_transaksi(request, pk):
    """Kasir mencatat cash untuk servis di bengkel."""
    transaksi = get_object_or_404(TransaksiServis, pk=pk)
    if request.method != "POST" and hasattr(transaksi, "pembayaran"):
        return redirect("pembayaran_nota", pk=transaksi.pembayaran.pk)
    if transaksi.status != TransaksiServis.STATUS_SELESAI:
        messages.error(request, "Pembayaran hanya dapat diproses untuk transaksi berstatus Selesai.")
        return redirect("kasir_transaksi_detail", pk=transaksi.pk)
    if request.method == "POST":
        form = CashForm(request.POST)
        if form.is_valid():
            try:
                pembayaran = Pembayaran.catat_cash(
                    transaksi, form.cleaned_data["uang_dibayar"], oleh=request.user)
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            else:
                messages.success(request, "Pembayaran berhasil dicatat.")
                return redirect("pembayaran_nota", pk=pembayaran.pk)
    else:
        form = CashForm()
    return render(request, "pembayaran/bayar.html", {
        "transaksi": transaksi,
        "form": form,
        "bukti_menunggu": BuktiPembayaran.menunggu_untuk(transaksi),
    })


@mekanik_required
@require_POST
def cash_mekanik(request, pk):
    """Mekanik mencatat cash yang diterimanya di lokasi home service."""
    transaksi = get_object_or_404(TransaksiServis, pk=pk, mekanik=request.mekanik)
    form = CashForm(request.POST)
    if not form.is_valid():
        for galat in form.errors.get("uang_dibayar", []):
            messages.error(request, galat)
        return redirect("mekanik_detail", pk=pk)
    try:
        Pembayaran.catat_cash(transaksi, form.cleaned_data["uang_dibayar"], oleh=request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Pembayaran cash dicatat. Transaksi lunas.")
    return redirect("mekanik_detail", pk=pk)


@login_required
@pelanggan_required
def bayar_nontunai(request, pk):
    """Pelanggan memilih transfer bank / e-money, membayar lewat QRIS/rekening, lalu unggah bukti."""
    profil = request.user.profil_pelanggan
    transaksi = get_object_or_404(TransaksiServis, pk=pk, pelanggan=profil)
    if hasattr(transaksi, "pembayaran"):
        return redirect("pembayaran_nota", pk=transaksi.pembayaran.pk)
    if request.method == "POST":
        form = BuktiPembayaranForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                BuktiPembayaran.ajukan(transaksi, profil, **form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, " ".join(exc.messages))
            else:
                messages.success(request, "Bukti terkirim. Kasir/admin akan memeriksanya.")
                return redirect("riwayat_service_detail", pk=pk)
    else:
        form = BuktiPembayaranForm()
    return render(request, "pembayaran/nontunai.html", {
        "transaksi": transaksi,
        "form": form,
        "riwayat_bukti": transaksi.bukti_pembayaran.select_related("diperiksa_oleh"),
        "bukti_menunggu": BuktiPembayaran.menunggu_untuk(transaksi),
        "nav": "riwayat_service",
    })


@login_required
def bukti_berkas(request, pk):
    """Berkas bukti hanya untuk kasir, admin, dan pelanggan pemilik transaksinya."""
    bukti = get_object_or_404(BuktiPembayaran.objects.select_related("transaksi__pelanggan"), pk=pk)
    user = request.user
    pelanggan = bukti.transaksi.pelanggan
    pemilik = pelanggan is not None and pelanggan.user_id == user.pk
    if not (user.is_superuser or user.role in ("KASIR", "ADMIN") or pemilik):
        raise Http404
    try:
        berkas = bukti.berkas.open("rb")
    except FileNotFoundError:
        raise Http404
    jenis, _ = mimetypes.guess_type(bukti.berkas.name)
    return FileResponse(berkas, content_type=jenis or "application/octet-stream")


@role_required("KASIR", "ADMIN")
def verifikasi_daftar(request):
    semua = BuktiPembayaran.objects.select_related(
        "transaksi", "transaksi__pelanggan__user", "transaksi__kendaraan", "diperiksa_oleh")
    return render(request, "pembayaran/verifikasi_daftar.html", {
        "menunggu": semua.filter(status=BuktiPembayaran.STATUS_MENUNGGU).order_by("diunggah_pada"),
        "selesai": semua.exclude(status=BuktiPembayaran.STATUS_MENUNGGU).order_by("-diperiksa_pada")[:20],
    })


@role_required("KASIR", "ADMIN")
def verifikasi_detail(request, pk):
    bukti = get_object_or_404(
        BuktiPembayaran.objects.select_related("transaksi", "transaksi__pelanggan__user",
                                               "transaksi__kendaraan", "diperiksa_oleh"), pk=pk)
    t = bukti.transaksi
    return render(request, "pembayaran/verifikasi_detail.html", {
        "bukti": bukti,
        "pdf": bukti.berkas.name.lower().endswith(".pdf"),
        "form_tolak": TolakBuktiForm(),
        # Rincian tagihan untuk dicocokkan dengan nominal di bukti.
        "detail_layanan": t.detail_servis.select_related("jenis_servis"),
        "detail_sparepart": t.detail_sparepart.select_related("sparepart"),
        "bukti_lain": t.bukti_pembayaran.exclude(pk=bukti.pk).select_related("diperiksa_oleh")
                       .order_by("-diunggah_pada"),
    })


@role_required("KASIR", "ADMIN")
@require_POST
def verifikasi_setujui(request, pk):
    bukti = get_object_or_404(BuktiPembayaran, pk=pk)
    try:
        pembayaran = bukti.setujui(request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("pembayaran_verifikasi_detail", pk=pk)
    messages.success(request, "Pembayaran disetujui. Transaksi lunas.")
    return redirect("pembayaran_nota", pk=pembayaran.pk)


@role_required("KASIR", "ADMIN")
@require_POST
def verifikasi_tolak(request, pk):
    bukti = get_object_or_404(BuktiPembayaran, pk=pk)
    try:
        bukti.tolak(request.user, request.POST.get("alasan", ""))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("pembayaran_verifikasi_detail", pk=pk)
    messages.success(request, "Bukti ditolak. Pelanggan akan melihat alasannya.")
    return redirect("pembayaran_verifikasi_daftar")


@login_required
def nota_pembayaran(request, pk):
    """
    Nota bisa dibuka kasir, admin, dan PELANGGAN PEMILIK transaksinya sendiri.
    Pelanggan lain tetap ditolak (FR-25).
    """
    pembayaran = get_object_or_404(
        Pembayaran.objects.select_related("transaksi__pelanggan__user", "transaksi__kendaraan",
                                          "dicatat_oleh"), pk=pk
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
