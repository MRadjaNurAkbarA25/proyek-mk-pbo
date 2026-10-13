"""Halaman mekanik hasil pemecahan menu sesuai desain:
Antrian Servis Masuk, Pengerjaan & Diagnosis, Panggilan Home Service, Profil & Keahlian.

Isinya sama dengan halaman antrian lama, hanya dipisah per menu.
"""
from django.contrib import messages
from django.shortcuts import redirect, render

from servis.models import TransaksiServis as T

from .decorators import mekanik_required
from .forms import StatusKetersediaanForm
from .forms_profil import ProfilMekanikForm
from .views import RELASI, STATUS_PEKERJAAN_SAYA


@mekanik_required
def pengerjaan_diagnosis(request):
    """Pekerjaan yang sedang dipegang mekanik ini, plus riwayat terakhirnya."""
    mekanik = request.mekanik
    mekanik.perbarui_status_otomatis()
    semua = T.objects.select_related(*RELASI).filter(mekanik=mekanik)
    context = {
        "pekerjaan_saya": semua.filter(status__in=STATUS_PEKERJAAN_SAYA).order_by("tanggal"),
        "riwayat": semua.filter(status__in=[T.STATUS_SELESAI, T.STATUS_DIBATALKAN]).order_by("-tanggal")[:10],
    }
    return render(request, "mekanik/pengerjaan.html", context)


@mekanik_required
def panggilan_home_service(request):
    """FR-18: panggilan home service yang menunggu jawaban mekanik ini."""
    mekanik = request.mekanik
    mekanik.perbarui_status_otomatis()
    semua = T.objects.select_related(*RELASI).filter(mekanik=mekanik)
    context = {
        "permintaan": semua.filter(status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK).order_by("tanggal"),
        "berjalan": semua.filter(
            tipe_layanan=T.TIPE_HOME_SERVICE, status__in=STATUS_PEKERJAAN_SAYA
        ).order_by("tanggal"),
    }
    return render(request, "mekanik/home_service.html", context)


@mekanik_required
def profil_mekanik(request):
    """Profil & keahlian mekanik yang sedang login."""
    mekanik = request.mekanik
    mekanik.perbarui_status_otomatis()

    if request.method == "POST":
        form = ProfilMekanikForm(request.POST, instance=mekanik)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil berhasil diperbarui.")
            return redirect("mekanik_profil")
    else:
        form = ProfilMekanikForm(instance=mekanik)

    context = {
        "mekanik": mekanik,
        "form": form,
        "jumlah_servis": mekanik.jumlah_servis,
        "sibuk": mekanik.punya_pekerjaan_berjalan(),
        "form_status": StatusKetersediaanForm(initial={"status": mekanik.status}),
    }
    return render(request, "mekanik/profil.html", context)
