from django import forms

from .models import JenisServis


class JenisServisForm(forms.ModelForm):
    """Form CRUD Jenis Servis (dikelola Admin)."""

    class Meta:
        model = JenisServis
        fields = ["nama_servis", "deskripsi", "estimasi_waktu", "harga"]
        labels = {
            "nama_servis": "Nama Servis",
            "deskripsi": "Deskripsi",
            "estimasi_waktu": "Estimasi Waktu (menit)",
            "harga": "Harga (Rp)",
        }
        widgets = {
            "deskripsi": forms.Textarea(attrs={"rows": 3}),
            "harga": forms.NumberInput(attrs={"step": "1000", "min": "0"}),
            "estimasi_waktu": forms.NumberInput(attrs={"min": "1"}),
        }

    def clean_harga(self):
        harga = self.cleaned_data["harga"]
        if harga < 0:
            raise forms.ValidationError("Harga tidak boleh negatif.")
        return harga
