"""Endpoint publik chat FAQ: tanpa login, hanya membaca, tidak menyimpan riwayat percakapan."""
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .models import PertanyaanFAQ, info_bengkel
from .pencocokan import jenis_sapaan

PANJANG_MAKS_KETIKAN = 200


@require_GET
@never_cache
def daftar(request):
    """Kategori beserta pertanyaan dan jawabannya yang aktif."""
    return JsonResponse({"kategori": PertanyaanFAQ.kategori_aktif()})


@require_GET
@never_cache
def cari(request):
    """Sampai 3 FAQ paling cocok dengan ?q=.

    jenis: "sapaan" / "terima_kasih" / "cari"; yakin: jawaban teratas jelas unggul.
    """
    teks = request.GET.get("q", "")[:PANJANG_MAKS_KETIKAN]
    jenis = jenis_sapaan(teks)
    if jenis:
        return JsonResponse({"hasil": [], "yakin": False, "jenis": jenis})
    hasil, yakin = PertanyaanFAQ.cari_lengkap(teks)
    info = info_bengkel()
    return JsonResponse({"hasil": [f.sebagai_dict(info) for f, _ in hasil], "yakin": yakin, "jenis": "cari"})
