# pelanggan/forms.py
from django import forms
from kendaraan.models import Kendaraan, Mobil, Motor, Truk

# Form Dasar (Atribut yang dimiliki semua kendaraan)
class KendaraanBaseForm(forms.ModelForm):
    class Meta:
        model = Kendaraan
        fields = ['no_polisi', 'merk', 'model_kendaraan', 'tahun']
        widgets = {
            'no_polisi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: B 1234 XYZ'}),
            'merk': forms.TextInput(attrs={'class': 'form-control'}),
            'model_kendaraan': forms.TextInput(attrs={'class': 'form-control'}),
            'tahun': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Form Khusus Mobil (Inheritance dari BaseForm)
class MobilForm(KendaraanBaseForm):
    class Meta(KendaraanBaseForm.Meta):
        model = Mobil
        fields = KendaraanBaseForm.Meta.fields + ['jumlah_pintu', 'jenis_mobil']
        widgets = {
            **KendaraanBaseForm.Meta.widgets,
            'jumlah_pintu': forms.NumberInput(attrs={'class': 'form-control'}),
            'jenis_mobil': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SUV, Sedan, MPV'}),
        }

# Form Khusus Motor
class MotorForm(KendaraanBaseForm):
    class Meta(KendaraanBaseForm.Meta):
        model = Motor
        fields = KendaraanBaseForm.Meta.fields + ['jenis_motor', 'kapasitas_mesin']
        widgets = {
            **KendaraanBaseForm.Meta.widgets,
            'jenis_motor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Matic, Bebek, Sport'}),
            'kapasitas_mesin': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'dalam cc'}),
        }

# Form Khusus Truk
class TrukForm(KendaraanBaseForm):
    class Meta(KendaraanBaseForm.Meta):
        model = Truk
        fields = KendaraanBaseForm.Meta.fields + ['kapasitas_muatan_kg', 'jumlah_sumbu']
        widgets = {
            **KendaraanBaseForm.Meta.widgets,
            'kapasitas_muatan_kg': forms.NumberInput(attrs={'class': 'form-control'}),
            'jumlah_sumbu': forms.NumberInput(attrs={'class': 'form-control'}),
        }