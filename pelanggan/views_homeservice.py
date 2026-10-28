from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from accounts.models import Mekanik
from servis.models import TransaksiServis
from accounts.decorators import pelanggan_required
from .forms import HomeServiceForm
from .views import pilihan_jenis


@login_required
@pelanggan_required
def pesan_home_service(request):
    """Pelanggan memesan servis di lokasi dan memilih mekanik yang tersedia."""
    profil = request.user.profil_pelanggan
    form = HomeServiceForm(request.POST or None, pelanggan=profil,
                           kendaraan_awal=request.GET.get("kendaraan", "").strip())

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
                    # buka() memeriksa ulang aturan satu kendaraan di dalam transaksi
                    # database (bisa saja dipesan dari tab lain) dan menulis linimasa.
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
                        # Kendaraannya di rumah pelanggan; bawaan True hanya untuk
                        # transaksi kasir di meja.
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
        "pilihan_jenis": pilihan_jenis(),
    }
    return render(request, "pelanggan/home_service.html", context)
