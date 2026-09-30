from django import forms
from .models import Mobil, Motor, Truk


class MobilForm(forms.ModelForm):
    class Meta:
        model = Mobil
        fields = ["no_polisi", "merk", "model_kendaraan", "tahun", "jumlah_pintu", "jenis_mobil"]


class MotorForm(forms.ModelForm):
    class Meta:
        model = Motor
        fields = ["no_polisi", "merk", "model_kendaraan", "tahun", "jenis_motor", "kapasitas_mesin"]


class TrukForm(forms.ModelForm):
    class Meta:
        model = Truk
        fields = ["no_polisi", "merk", "model_kendaraan", "tahun", "kapasitas_muatan_kg", "jumlah_sumbu"]