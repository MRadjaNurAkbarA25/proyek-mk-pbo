from django import forms
from .models import Sparepart

class SparepartForm(forms.ModelForm):
    class Meta:
        model = Sparepart
        # FR-35: 'stok' sengaja TIDAK ikut. Stok tidak boleh diketik manual —
        # stok bertambah lewat Pembelian, berkurang saat dipakai servis.
        fields = ['kode', 'nama', 'kategori', 'harga', 'stok_minimum']
        widgets = {
            'kode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan Kode Sparepart'}),
            'nama': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan Nama Sparepart'}),
            'kategori': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan Kategori'}),
            'harga': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000'}),
            'stok_minimum': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class SparepartFilterForm(forms.Form):
    q = forms.CharField(
        required=False, 
        label='Cari',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cari nama atau kode...'})
    )
    kategori = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter kategori...'})
    )
    stok_kritis = forms.BooleanField(
        required=False,
        # Centang ini menyaring stok habis sekaligus stok menipis, karena
        # keduanya sama-sama perlu dipesan ulang. Labelnya menyebut kondisi
        # stoknya langsung supaya tidak disangka "barang yang sudah dipesan".
        label='Hanya stok habis/menipis',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )