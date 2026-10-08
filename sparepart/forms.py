from django import forms
from .models import Sparepart

class SparepartForm(forms.ModelForm):
    class Meta:
        model = Sparepart
        fields = ['kode', 'nama', 'kategori', 'harga', 'stok', 'stok_minimum']
        widgets = {
            'kode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan Kode Sparepart'}),
            'nama': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan Nama Sparepart'}),
            'kategori': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan Kategori'}),
            'harga': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000'}),
            'stok': forms.NumberInput(attrs={'class': 'form-control'}),
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
        label='Hanya Stok Minimum',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )