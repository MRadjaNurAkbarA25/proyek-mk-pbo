"""View FR-35: Supplier dan Pembelian Sparepart (role ADMIN).

Semua aturan bisnis (draf vs selesai, tambah/hapus barang, penambahan stok)
hidup di method model. View di sini hanya membungkus form dan memanggil
method itu — tidak ada satu pun view yang menyentuh kolom stok secara
langsung (NFR-4: encapsulation).
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from bengkel_project.paginasi import PER_HALAMAN_TABEL, halaman_dari

from .forms import DetailPembelianForm, PembelianForm, SupplierForm
from .models import DetailPembelian, PembelianSparepart, Supplier


# =====================================================================
# Supplier
# =====================================================================

@role_required("ADMIN")
def supplier_daftar(request):
    """Daftar supplier + pencarian + jumlah pembelian + paginasi."""
    daftar = Supplier.objects.annotate(
        jumlah_pembelian=Count("pembelian", distinct=True),
    )
    kata_kunci = request.GET.get("q", "").strip()
    if kata_kunci:
        daftar = daftar.filter(
            Q(nama__icontains=kata_kunci)
            | Q(telepon__icontains=kata_kunci)
        )
    daftar = daftar.order_by("-aktif", "nama")
    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)
    return render(request, "pembelian/supplier_daftar.html", {
        "daftar": halaman, "halaman": halaman, "kata_kunci": kata_kunci,
    })


@role_required("ADMIN")
def supplier_tambah(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        supplier = form.save()
        messages.success(request, f"Supplier '{supplier.nama}' berhasil ditambahkan.")
        return redirect("pembelian:supplier_list")
    return render(request, "pembelian/supplier_form.html", {
        "form": form, "judul": "Tambah Supplier",
        "keterangan": "Daftarkan pemasok baru. Supplier tidak bisa dihapus, hanya dinonaktifkan.",
    })


@role_required("ADMIN")
def supplier_ubah(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        supplier = form.save()
        messages.success(request, f"Data supplier '{supplier.nama}' berhasil diperbarui.")
        return redirect("pembelian:supplier_list")
    return render(request, "pembelian/supplier_form.html", {
        "form": form, "judul": f"Ubah Supplier: {supplier.nama}",
        "keterangan": "Perbarui data pemasok. Status aktif/nonaktif diubah lewat daftar, bukan di sini.",
    })


@role_required("ADMIN")
@require_POST
def supplier_ubah_status(request, pk):
    """Nonaktifkan/aktifkan supplier. Pola sama dengan akun (FR-35)."""
    supplier = get_object_or_404(Supplier, pk=pk)
    try:
        if request.POST.get("aktif") == "1":
            supplier.aktifkan()
            messages.success(request, f"Supplier '{supplier.nama}' diaktifkan kembali.")
        else:
            supplier.nonaktifkan()
            messages.success(request, f"Supplier '{supplier.nama}' dinonaktifkan.")
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))

    tujuan = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(tujuan, allowed_hosts={request.get_host()}):
        tujuan = "pembelian:supplier_list"
    return redirect(tujuan)


# =====================================================================
# Pembelian Sparepart
# =====================================================================

def _pembelian_atau_404(pk):
    return get_object_or_404(PembelianSparepart, pk=pk)


def _eksekusi(request, pembelian, aksi, pesan_sukses, tujuan_detail=True):
    """Jalankan aksi model lalu tangkap ValidationError (pola mekanik/views.py)."""
    try:
        aksi()
        messages.success(request, pesan_sukses)
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    if tujuan_detail:
        return redirect("pembelian:pembelian_detail", pk=pembelian.pk)
    return redirect("pembelian:pembelian_list")


@role_required("ADMIN")
def pembelian_daftar(request):
    """Daftar seluruh pembelian + filter kata kunci dan status."""
    daftar = PembelianSparepart.objects.select_related("supplier", "dicatat_oleh")
    kata_kunci = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if kata_kunci:
        daftar = daftar.filter(
            Q(kode__icontains=kata_kunci)
            | Q(supplier__nama__icontains=kata_kunci)
        )
    if status in (PembelianSparepart.STATUS_DRAF, PembelianSparepart.STATUS_SELESAI):
        daftar = daftar.filter(status=status)
    halaman = halaman_dari(request, daftar, PER_HALAMAN_TABEL)
    return render(request, "pembelian/pembelian_daftar.html", {
        "daftar": halaman, "halaman": halaman, "kata_kunci": kata_kunci, "status": status,
    })


@role_required("ADMIN")
def pembelian_catat(request):
    """Buat draf pembelian baru. Stok belum berubah di tahap ini.

    Lewat ?sparepart=<pk> (tombol "Beli" di halaman stok), draf yang baru
    dibuat akan meneruskan pk itu ke halaman detail supaya form tambah
    barang langsung terisi sparepart tersebut.
    """
    form = PembelianForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pembelian = form.save(commit=False)
        pembelian.dicatat_oleh = request.user
        pembelian.save()
        messages.success(
            request,
            f"Draf {pembelian.kode} dibuat. Tambahkan barang, lalu klik 'Selesaikan'.",
        )
        tujuan = reverse("pembelian:pembelian_detail", args=[pembelian.pk])
        sparepart_pk = request.GET.get("sparepart", "")
        if sparepart_pk:
            tujuan += f"?sparepart={sparepart_pk}"
        return redirect(tujuan)
    return render(request, "pembelian/pembelian_form.html", {
        "form": form, "judul": "Catat Pembelian Baru",
    })


@role_required("ADMIN")
def pembelian_detail(request, pk):
    pembelian = _pembelian_atau_404(pk)
    sparepart_pk = request.GET.get("sparepart", "")
    awal = {"sparepart": sparepart_pk} if sparepart_pk else None
    form_tambah = DetailPembelianForm(initial=awal)
    return render(request, "pembelian/pembelian_detail.html", {
        "pembelian": pembelian, "form_tambah": form_tambah,
    })


@role_required("ADMIN")
@require_POST
def pembelian_tambah_barang(request, pk):
    pembelian = _pembelian_atau_404(pk)
    form = DetailPembelianForm(request.POST)
    if form.is_valid():
        aksi = lambda: pembelian.tambah_barang(
            form.cleaned_data["sparepart"],
            form.cleaned_data["jumlah"],
            form.cleaned_data["harga_beli"],
        )
        return _eksekusi(request, pembelian, aksi, "Barang ditambahkan ke pembelian.")
    # Tampilkan error form (mis. jumlah/harga <= 0)
    for galat in form.errors.values():
        for pesan in galat:
            messages.error(request, pesan)
    return redirect("pembelian:pembelian_detail", pk=pembelian.pk)


@role_required("ADMIN")
@require_POST
def pembelian_hapus_barang(request, pk, detail_pk):
    pembelian = _pembelian_atau_404(pk)
    detail = get_object_or_404(DetailPembelian, pk=detail_pk, pembelian=pembelian)
    aksi = lambda: pembelian.hapus_barang(detail)
    return _eksekusi(request, pembelian, aksi, "Barang dihapus dari pembelian.")


@role_required("ADMIN")
@require_POST
def pembelian_selesaikan(request, pk):
    """Panggil selesaikan() — satu-satunya jalan stok bertambah."""
    pembelian = _pembelian_atau_404(pk)
    return _eksekusi(request, pembelian, pembelian.selesaikan, "Pembelian selesai, stok bertambah.")


@role_required("ADMIN")
@require_POST
def pembelian_hapus(request, pk):
    """Hapus draf. Pembelian SELESAI tidak bisa dihapus (dijaga model)."""
    pembelian = _pembelian_atau_404(pk)
    return _eksekusi(request, pembelian, pembelian.hapus_draf, "Draf pembelian dihapus.", tujuan_detail=False)