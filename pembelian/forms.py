"""Form FR-35: Supplier dan Pembelian Sparepart (widget KONTROL dan PILIHAN)."""
from django import forms
from django.utils import timezone

from .models import PembelianSparepart, Supplier
from sparepart.models import Sparepart

KONTROL = {"class": "form-control"}
PILIHAN = {"class": "form-select"}


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        # 'aktif' sengaja tidak ikut: status diubah lewat tombol
        # Nonaktifkan/Aktifkan di daftar, bukan lewat form ini.
        fields = ["nama", "telepon", "alamat", "catatan"]
        widgets = {
            "nama": forms.TextInput(attrs={**KONTROL, "placeholder": "Nama supplier"}),
            "telepon": forms.TextInput(attrs={**KONTROL, "placeholder": "08xx / nomor WhatsApp"}),
            "alamat": forms.Textarea(attrs={**KONTROL, "rows": 2}),
            "catatan": forms.Textarea(attrs={**KONTROL, "rows": 2}),
        }


class PembelianForm(forms.ModelForm):
    class Meta:
        model = PembelianSparepart
        fields = ["supplier", "tanggal", "metode_bayar"]
        widgets = {
            "supplier": forms.Select(attrs=PILIHAN),
            "tanggal": forms.DateInput(attrs={**KONTROL, "type": "date"}),
            "metode_bayar": forms.Select(attrs=PILIHAN),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hanya supplier yang masih aktif yang boleh dipilih (FR-35).
        self.fields["supplier"].queryset = Supplier.objects.filter(aktif=True)
        if "tanggal" in self.fields and not self.initial.get("tanggal"):
            self.fields["tanggal"].initial = timezone.localdate()


class DetailPembelianForm(forms.Form):
    """Satu barang untuk draf pembelian; semua sparepart ditampilkan, termasuk stok 0."""

    sparepart = forms.ModelChoiceField(
        queryset=Sparepart.objects.all(),
        empty_label="-- pilih sparepart --",
        widget=forms.Select(attrs=PILIHAN),
    )
    jumlah = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs=KONTROL),
    )
    harga_beli = forms.DecimalField(
        min_value=1,
        max_digits=12,
        decimal_places=2,
        label="Harga Beli Satuan",
        widget=forms.NumberInput(attrs={**KONTROL, "step": "1000"}),
    )