from django import forms

from .models import Pembayaran


class PembayaranForm(forms.Form):
    metode = forms.ChoiceField(choices=Pembayaran.METODE_CHOICES, widget=forms.RadioSelect)
    uang_dibayar = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=12)
    nomor_referensi = forms.CharField(required=False, max_length=100)
    provider = forms.CharField(required=False, max_length=50)
    nomor_transaksi = forms.CharField(required=False, max_length=100)

    def clean(self):
        data = super().clean()
        metode = data.get("metode")
        if metode == Pembayaran.METODE_CASH and data.get("uang_dibayar") is None:
            self.add_error("uang_dibayar", "Nominal pembayaran cash wajib diisi.")
        elif metode == Pembayaran.METODE_TRANSFER and not (data.get("nomor_referensi") or "").strip():
            self.add_error("nomor_referensi", "Nomor referensi transfer wajib diisi.")
        elif metode == Pembayaran.METODE_EWALLET:
            if not (data.get("provider") or "").strip():
                self.add_error("provider", "Provider E-Wallet wajib diisi.")
            if not (data.get("nomor_transaksi") or "").strip():
                self.add_error("nomor_transaksi", "Nomor transaksi E-Wallet wajib diisi.")
        return data
