from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from accounts.decorators import role_required
from bengkel_project.paginasi import PER_HALAMAN_PADAT, halaman_dari
from django.db.models import Q, F, ProtectedError
from .models import Sparepart
from .forms import SparepartForm, SparepartFilterForm

@role_required("ADMIN", "KASIR", "MEKANIK")
def sparepart_list(request):
    """Menampilkan daftar sparepart, pencarian, dan alert stok minimum (FR-21, FR-23)."""
    queryset = Sparepart.objects.all()
    filter_form = SparepartFilterForm(request.GET)
    
    if filter_form.is_valid():
        q = filter_form.cleaned_data.get('q')
        kategori = filter_form.cleaned_data.get('kategori')
        hanya_stok_kritis = filter_form.cleaned_data.get('stok_kritis')

        if q:
            queryset = queryset.filter(Q(nama__icontains=q) | Q(kode__icontains=q))
        if kategori:
            queryset = queryset.filter(kategori__icontains=kategori)
        if hanya_stok_kritis:
            queryset = queryset.filter(stok__lte=F('stok_minimum'))

    # Daftar sparepart yang perlu dipesan ulang: habis atau sudah di batas
    # minimum (FR-23). Dipisah dua angka supaya peringatannya bisa membedakan
    # "servis berhenti" dari "segera pesan".
    kritis_qs = Sparepart.objects.filter(stok__lte=F('stok_minimum'))
    jumlah_kritis = kritis_qs.count()
    jumlah_kosong = Sparepart.objects.filter(stok__lte=0).count()

    halaman = halaman_dari(request, queryset, PER_HALAMAN_PADAT)

    context = {
        'spareparts': halaman,
        'halaman': halaman,
        'filter_form': filter_form,
        'stok_kritis_count': jumlah_kritis,
        'stok_kosong_count': jumlah_kosong,
        'stok_menipis_count': jumlah_kritis - jumlah_kosong,
        'stok_kritis_items': kritis_qs,
    }
    return render(request, 'sparepart/sparepart_list.html', context)

@role_required("ADMIN")
def sparepart_create(request):
    """Menambah data sparepart baru oleh Admin (FR-21)."""
    if request.method == 'POST':
        form = SparepartForm(request.POST)
        if form.is_valid():
            sp = form.save()
            messages.success(request, f"Sparepart '{sp.nama}' berhasil ditambahkan.")
            return redirect('sparepart:sparepart_list')
    else:
        form = SparepartForm()

    return render(request, 'sparepart/sparepart_form.html', {'form': form, 'title': 'Tambah Sparepart'})

@role_required("ADMIN")
def sparepart_update(request, pk):
    """Mengubah data sparepart oleh Admin (FR-21)."""
    sparepart = get_object_or_404(Sparepart, pk=pk)
    if request.method == 'POST':
        form = SparepartForm(request.POST, instance=sparepart)
        if form.is_valid():
            form.save()
            messages.success(request, f"Sparepart '{sparepart.nama}' berhasil diperbarui.")
            return redirect('sparepart:sparepart_list')
    else:
        form = SparepartForm(instance=sparepart)

    return render(request, 'sparepart/sparepart_form.html', {'form': form, 'title': 'Ubah Sparepart'})

@role_required("ADMIN")
def sparepart_delete(request, pk):
    """Menghapus data sparepart oleh Admin (FR-21)."""
    sparepart = get_object_or_404(Sparepart, pk=pk)
    if request.method == 'POST':
        nama = sparepart.nama
        try:
            sparepart.delete()
        except ProtectedError:
            # DetailSparepart memakai on_delete=PROTECT: sparepart yang sudah dipakai transaksi tidak boleh hilang.
            # FR-35: DetailPembelian juga PROTECT, jadi pesan mencakup keduanya.
            messages.error(request, f"Sparepart '{nama}' tidak bisa dihapus karena sudah dipakai di transaksi servis atau pembelian.")
            return redirect('sparepart:sparepart_list')
        messages.success(request, f"Sparepart '{nama}' berhasil dihapus.")
        return redirect('sparepart:sparepart_list')

    return render(request, 'sparepart/sparepart_confirm_delete.html', {'sparepart': sparepart})

@role_required("ADMIN", "KASIR", "MEKANIK")
def peringatan_stok(request):
    """Halaman/Laporan khusus peringatan stok minimum (FR-23, FR-29)."""
    # Diurutkan dari stok paling sedikit, jadi yang sudah habis muncul paling
    # atas — itu yang paling mendesak dipesan.
    kritis_qs = Sparepart.objects.filter(stok__lte=F('stok_minimum')).order_by('stok', 'nama')
    return render(request, 'sparepart/peringatan_stok.html', {'spareparts': kritis_qs})
