from django import forms

from kendaraan.models import Kendaraan


class BuatTransaksiForm(forms.Form):
    """FR-11: Kasir mencari kendaraan berdasarkan nomor polisi, lalu mencatat keluhan.

    Mengikuti pola `cari_kendaraan` yang sudah ada di `kasir/views.py` (query lewat
    subclass Mobil/Motor) agar polymorphism Kendaraan tetap terjaga.
    """

    no_polisi = forms.CharField(
        max_length=15,
        label="Nomor Polisi",
        widget=forms.TextInput(attrs={"placeholder": "Contoh: KT 1001 AA"}),
    )
    keluhan = forms.CharField(
        label="Keluhan Pelanggan",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Jelaskan keluhan..."}),
    )

    def clean_no_polisi(self):
        no_polisi = (self.cleaned_data.get("no_polisi") or "").strip()
        if not no_polisi:
            raise forms.ValidationError("Nomor polisi wajib diisi.")

        # Cari lewat subclass agar instance Mobil/Motor yang tersimpan.
        for Model in Kendaraan.model_subkelas():
            kendaraan = Model.objects.filter(
                no_polisi__iexact=no_polisi
            ).select_related("pelanggan__user").first()
            if kendaraan:
                self.kendaraan = kendaraan
                return no_polisi

        raise forms.ValidationError(
            f"Kendaraan dengan nomor polisi '{no_polisi}' tidak ditemukan."
        )

    def clean_keluhan(self):
        keluhan = (self.cleaned_data.get("keluhan") or "").strip()
        if not keluhan:
            raise forms.ValidationError("Keluhan wajib diisi.")
        return keluhan
