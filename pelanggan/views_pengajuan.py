"""FR-31: pelanggan mengajukan servis di bengkel, lalu kasir menyetujuinya.

Beda dengan Home Service (FR-18): di sini pelanggan datang sendiri ke bengkel,
jadi tidak memilih mekanik dan tidak mengisi lokasi. Yang menyetujui kasir,
bukan mekanik.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from servis.models import PengajuanServis, TransaksiServis

from accounts.decorators import pelanggan_required
from .forms_pengajuan import PengajuanServisForm, TanggalDatangForm

RELASI = ("kendaraan__mobil", "kendaraan__motor", "kendaraan__truk", "transaksi")


@pelanggan_required
def ajukan_servis(request):
    """Form pengajuan servis. Setelah terkirim, menunggu persetujuan kasir."""
    profil = request.user.profil_pelanggan
    form = PengajuanServisForm(request.POST or None, pelanggan=profil)

    if request.method == "POST" and form.is_valid():
        kendaraan = form.cleaned_data["kendaraan"]

        # Pemeriksaan kepemilikan diulang di server walau pilihan form sudah
        # dibatasi, agar tidak bisa ditembus dengan request manual.
        if kendaraan.pelanggan_id != profil.pk:
            form.add_error("kendaraan", "Kendaraan tersebut bukan milik akun Anda.")
        else:
            pengajuan = PengajuanServis.objects.create(
                pelanggan=profil,
                kendaraan=kendaraan,
                keluhan=form.cleaned_data["keluhan"],
                tanggal_rencana_datang=form.cleaned_data["tanggal_rencana_datang"],
            )
            messages.success(
                request,
                f"Pengajuan servis untuk {pengajuan.kendaraan.no_polisi} sudah dikirim. "
                "Kasir akan meninjau dan mengabari lewat halaman ini.",
            )
            return redirect("pengajuan_saya")

    return render(request, "pelanggan/pengajuan_form.html", {
        "form": form,
        "ada_kendaraan": form.ada_kendaraan,
    })


@pelanggan_required
def pengajuan_saya(request):
    """Daftar pengajuan milik pelanggan yang login, terbaru di atas."""
    # FR-31 C: batalkan dulu transaksi yang kendaraannya tidak kunjung
    # datang, supaya daftar di bawah ini tidak menampilkan transaksi yang
    # sebenarnya sudah kedaluwarsa. Dipanggil dari sisi kasir MAUPUN
    # pelanggan: kalau hanya kasir, pelanggan bisa melihat transaksi yang
    # seharusnya sudah batal selama kasirnya belum membuka halaman.
    TransaksiServis.sapu_kedatangan_lewat()

    profil = request.user.profil_pelanggan
    daftar = PengajuanServis.objects.filter(pelanggan=profil).select_related(*RELASI)
    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)
    return render(request, "pelanggan/pengajuan_daftar.html", {
        "daftar": halaman,
        "halaman": halaman,
        "jumlah_menunggu": daftar.filter(status=PengajuanServis.STATUS_MENUNGGU).count(),
    })


@pelanggan_required
def ubah_tanggal_datang(request, pk):
    """Pelanggan mengubah rencana tanggal membawa kendaraannya.

    Dua keadaan, dua sasaran yang berbeda:

    * Pengajuan masih MENUNGGU -> yang diubah pengajuannya sendiri.
    * Pengajuan sudah DITERIMA -> yang diubah TRANSAKSINYA, bukan pengajuan.

    Pemisahan ini disengaja. Begitu kasir memutuskan, pengajuan berubah sifat
    menjadi catatan "apa yang diminta dan apa keputusannya". Kalau isinya masih
    bisa diubah pelanggan, catatan itu tidak bisa dipercaya lagi. Jadi yang
    berlaku setelah disetujui adalah salinan tanggal di transaksi.
    """
    pengajuan = get_object_or_404(
        PengajuanServis.objects.select_related(*RELASI),
        pk=pk,
        pelanggan=request.user.profil_pelanggan,
    )

    sasaran = None
    if pengajuan.masih_menunggu:
        sasaran = pengajuan
    elif pengajuan.transaksi and pengajuan.transaksi.tanggal_masih_bisa_diubah:
        sasaran = pengajuan.transaksi

    if sasaran is None:
        messages.error(
            request,
            "Tanggal kedatangan tidak bisa diubah lagi untuk pengajuan ini.",
        )
        return redirect("pengajuan_saya")

    form = TanggalDatangForm(
        request.POST or None,
        initial={"tanggal_rencana_datang": sasaran.tanggal_rencana_datang},
    )

    if request.method == "POST" and form.is_valid():
        tanggal = form.cleaned_data["tanggal_rencana_datang"]
        try:
            if sasaran is pengajuan:
                pengajuan.ubah_rencana_datang(tanggal)
            else:
                sasaran.ubah_rencana_datang(tanggal)
        except ValidationError as e:
            for pesan in e.messages:
                form.add_error("tanggal_rencana_datang", pesan)
        else:
            messages.success(
                request,
                "Rencana tanggal kedatangan diperbarui."
                if tanggal
                else "Tanggal kedatangan dikosongkan.",
            )
            return redirect("pengajuan_saya")

    return render(request, "pelanggan/pengajuan_tanggal.html", {
        "form": form,
        "pengajuan": pengajuan,
        "sudah_diterima": sasaran is not pengajuan,
    })


@require_POST
@pelanggan_required
def batalkan_pengajuan(request, pk):
    """Pelanggan menarik kembali pengajuan yang belum diproses kasir."""
    pengajuan = get_object_or_404(
        PengajuanServis, pk=pk, pelanggan=request.user.profil_pelanggan
    )
    try:
        pengajuan.batalkan()
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        messages.success(
            request,
            f"Pengajuan untuk {pengajuan.kendaraan.no_polisi} sudah dibatalkan.",
        )
    return redirect("pengajuan_saya")
