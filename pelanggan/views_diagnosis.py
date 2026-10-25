from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from servis.models import PembaruanServis, TransaksiServis
from accounts.decorators import pelanggan_required

@login_required
@pelanggan_required
def persetujuan_diagnosis(request):
    """Tampilkan diagnosis yang sedang menunggu keputusan pelanggan."""
    profil = request.user.profil_pelanggan
    daftar = TransaksiServis.objects.filter(
        pelanggan=profil,
        status=TransaksiServis.STATUS_MENUNGGU_KONFIRMASI,
    ).select_related("kendaraan", "mekanik", "mekanik__user").prefetch_related(
        "detail_servis__jenis_servis", "detail_sparepart__sparepart",
    ).annotate(
        # Waktu mekanik mengirim diagnosis = baris linimasa tahap persetujuan
        # terakhir. Dihitung di query supaya tidak satu query per kartu.
        waktu_diagnosis=Max(
            "pembaruan__waktu",
            filter=Q(pembaruan__tahap=PembaruanServis.TAHAP_PERSETUJUAN),
        ),
    ).order_by("-tanggal")
    return render(request, "pelanggan/persetujuan_diagnosis.html", {"daftar": daftar})

@login_required
@pelanggan_required
@require_POST
def konfirmasi_diagnosis(request, pk):
    """Terima atau tolak diagnosis; transaksi wajib milik pelanggan yang login."""
    profil = request.user.profil_pelanggan
    transaksi = get_object_or_404(
        TransaksiServis.objects.select_related("mekanik"),
        pk=pk,
        pelanggan=profil,
    )
    aksi = request.POST.get("aksi")

    if aksi not in ("setuju", "tolak"):
        messages.error(request, "Pilihan konfirmasi tidak valid.")
        return redirect("persetujuan_diagnosis")

    try:
        transaksi.konfirmasi(aksi == "setuju")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        if aksi == "setuju":
            messages.success(
                request,
                f"Diagnosis {transaksi.kode_transaksi} disetujui. Servis dapat dikerjakan mekanik.",
            )
        else:
            messages.success(
                request,
                f"Diagnosis {transaksi.kode_transaksi} ditolak. Transaksi dibatalkan.",
            )

    return redirect("persetujuan_diagnosis")
