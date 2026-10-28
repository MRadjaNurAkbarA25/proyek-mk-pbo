"""Halaman menu mekanik: Antrian Servis Masuk, Pengerjaan & Diagnosis, Panggilan Home Service."""
from django.contrib import messages
from django.shortcuts import redirect, render

from servis.models import TransaksiServis as T

from accounts.decorators import mekanik_required
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
    """URL lama; Profil & Keahlian ada di halaman Profil Saya bersama."""
    return redirect("profil_saya")


