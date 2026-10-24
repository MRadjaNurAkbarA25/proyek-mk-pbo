"""Endpoint publik untuk jendela chat FAQ. Terbuka tanpa login (pengunjung
landing page belum punya akun), hanya membaca, dan tidak menyimpan apa pun,
jadi riwayat percakapan tidak pernah tersimpan."""
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .models import PertanyaanFAQ

PANJANG_MAKS_KETIKAN = 200


@require_GET
@never_cache
def daftar(request):
    """Kategori beserta pertanyaan dan jawabannya yang aktif."""
    return JsonResponse({"kategori": PertanyaanFAQ.kategori_aktif()})


@require_GET
@never_cache
def cari(request):
    """Sampai 3 FAQ yang paling cocok dengan ?q=. Kosong kalau tidak ada yang cocok."""
    teks = request.GET.get("q", "")[:PANJANG_MAKS_KETIKAN]
    return JsonResponse({"hasil": [f.sebagai_dict() for f in PertanyaanFAQ.cari(teks)]})
