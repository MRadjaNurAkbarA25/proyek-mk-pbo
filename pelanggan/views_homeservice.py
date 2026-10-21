from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from accounts.models import Mekanik
from servis.models import TransaksiServis
from accounts.decorators import pelanggan_required
from .forms import HomeServiceForm


@login_required
@pelanggan_required
def pesan_home_service(request):
    """Pelanggan memesan servis di lokasi dan memilih mekanik yang tersedia."""
    profil = request.user.profil_pelanggan
    form = HomeServiceForm(request.POST or None, pelanggan=profil)

    if request.method == "POST" and form.is_valid():
        kendaraan = form.cleaned_data["kendaraan"]
        mekanik_pilihan = form.cleaned_data["mekanik"]

        # Pemeriksaan kepemilikan di sisi server tetap dilakukan walau pilihan form
        # sudah dibatasi, agar data tidak bisa dimanipulasi melalui request manual.
        if kendaraan.pelanggan_id != profil.pk:
            form.add_error("kendaraan", "Kendaraan tersebut bukan milik akun Anda.")
        else:
            try:
                with transaction.atomic():
                    mekanik = Mekanik.objects.select_for_update().get(
                        pk=mekanik_pilihan.pk,
                        status=Mekanik.STATUS_TERSEDIA,
                        user__role="MEKANIK",
                    )
                    # buka() memeriksa ulang aturan satu kendaraan DI DALAM
                    # transaksi database ini, bukan hanya di form: antara form
                    # divalidasi dan baris ini, kendaraan yang sama bisa saja
                    # sudah dipesan lewat tab lain. Pemeriksaan di form untuk
                    # pesan yang enak dibaca; yang ini yang menjaga datanya.
                    # buka() juga menulis baris pertama linimasa.
                    transaksi = TransaksiServis.buka(
                        keterangan=(
                            f"Panggilan home service dikirim ke mekanik "
                            f"{mekanik.user.nama_tampil}."
                        ),
                        oleh=request.user,
                        pelanggan=profil,
                        kendaraan=kendaraan,
                        mekanik=mekanik,
                        keluhan=form.cleaned_data["keluhan"],
                        tipe_layanan=TransaksiServis.TIPE_HOME_SERVICE,
                        lokasi_servis=form.cleaned_data["lokasi_servis"],
                        status=TransaksiServis.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
                        # Kendaraannya ada di rumah pelanggan, bukan di
                        # bengkel. Nilai bawaan field ini True karena
                        # transaksi yang dibuat kasir di meja memang
                        # kendaraannya sudah di depan mata; home service
                        # kebalikannya. Tidak membuat transaksi ini dianggap
                        # "menunggu kedatangan" — properti itu hanya berlaku
                        # untuk pekerjaan di bengkel.
                        kendaraan_hadir=False,
                    )
            except Mekanik.DoesNotExist:
                form.add_error(
                    "mekanik",
                    "Mekanik tersebut tidak lagi tersedia. Silakan pilih mekanik lain.",
                )
            except ValidationError as exc:
                form.add_error("kendaraan", " ".join(exc.messages))
            else:
                messages.success(
                    request,
                    f"Pesanan Home Service {transaksi.kode_transaksi} berhasil dikirim. "
                    "Menunggu mekanik menerima permintaan Anda.",
                )
                return redirect("pelanggan_dashboard")

    context = {
        "form": form,
        "ada_kendaraan": bool(form._kendaraan_by_value),
        "ada_mekanik": form.fields["mekanik"].queryset.exists(),
    }
    return render(request, "pelanggan/home_service.html", context)
