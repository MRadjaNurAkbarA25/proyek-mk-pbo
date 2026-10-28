"""Kelola FAQ (FR-34): daftar, tambah, ubah, nonaktifkan/aktifkan (FAQ tidak dihapus)."""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari
from faq.models import PertanyaanFAQ
from faq.views import PANJANG_MAKS_KETIKAN

from .forms import PertanyaanFAQForm


@role_required("ADMIN")
def daftar_faq(request):
    daftar = PertanyaanFAQ.objects.all()
    kategori = request.GET.get("kategori", "")
    if kategori in dict(PertanyaanFAQ.KATEGORI_CHOICES):
        daftar = daftar.filter(kategori=kategori)
    else:
        kategori = ""
    kata_kunci = request.GET.get("q", "").strip()
    if kata_kunci:
        daftar = daftar.filter(
            Q(pertanyaan__icontains=kata_kunci)
            | Q(jawaban__icontains=kata_kunci)
            | Q(kata_kunci__icontains=kata_kunci)
        )
    # Aktif dulu, lalu menurut kategori dan urutan tampil di chat.
    urutan_kategori = [kode for kode, _ in PertanyaanFAQ.KATEGORI_CHOICES]
    daftar = sorted(daftar, key=lambda f: (not f.aktif, urutan_kategori.index(f.kategori), f.urutan, f.pk))
    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)

    # "Coba pertanyaan": hanya dihitung untuk ditampilkan, tidak disimpan.
    coba = request.GET.get("coba", "").strip()[:PANJANG_MAKS_KETIKAN]
    coba_hasil = coba_token = None
    if coba:
        hasil, _ = PertanyaanFAQ.cari_lengkap(coba, batas=5)
        coba_hasil = [{"faq": f, "skor": skor} for f, skor in hasil]
        coba_token = PertanyaanFAQ.token_ketikan(coba)
    return render(request, "adminpanel/faq_daftar.html", {
        "daftar": halaman, "halaman": halaman, "kata_kunci": kata_kunci,
        "kategori_pilih": kategori, "kategori_choices": PertanyaanFAQ.KATEGORI_CHOICES,
        "coba": coba, "coba_hasil": coba_hasil, "coba_token": coba_token,
    })


@role_required("ADMIN")
def tambah_faq(request):
    form = PertanyaanFAQForm(request.POST or None, initial={"aktif": True})
    if request.method == "POST" and form.is_valid():
        faq = form.save()
        messages.success(request, f"FAQ '{faq.pertanyaan}' berhasil ditambahkan.")
        return redirect("kelola_faq")
    return render(request, "adminpanel/faq_form.html", {
        "form": form, "judul": "Tambah FAQ", "mode_tambah": True,
    })


@role_required("ADMIN")
def ubah_faq(request, pk):
    faq = get_object_or_404(PertanyaanFAQ, pk=pk)
    form = PertanyaanFAQForm(request.POST or None, instance=faq)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"FAQ '{faq.pertanyaan}' berhasil diperbarui.")
        return redirect("kelola_faq")
    return render(request, "adminpanel/faq_form.html", {
        "form": form, "judul": "Ubah FAQ", "faq": faq, "mode_tambah": False,
    })


@role_required("ADMIN")
@require_POST
def ubah_status_faq(request, pk):
    """Nonaktifkan (aktif=0) atau aktifkan (aktif=1) sebuah FAQ."""
    faq = get_object_or_404(PertanyaanFAQ, pk=pk)
    if request.POST.get("aktif") == "1":
        faq.aktifkan()
        messages.success(request, f"FAQ '{faq.pertanyaan}' diaktifkan kembali.")
    else:
        faq.nonaktifkan()
        messages.success(request, f"FAQ '{faq.pertanyaan}' dinonaktifkan. Tidak tampil di chat, tapi tidak dihapus.")

    tujuan = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(tujuan, allowed_hosts={request.get_host()}):
        tujuan = "kelola_faq"
    return redirect(tujuan)
