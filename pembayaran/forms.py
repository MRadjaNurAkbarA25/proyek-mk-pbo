from django import forms

from .models import BuktiPembayaran


class CashForm(forms.Form):
    """Petugas (kasir di bengkel, mekanik di home service) mencatat uang tunai."""

    uang_dibayar = forms.DecimalField(min_value=0, decimal_places=2, max_digits=12,
                                      label="Uang dibayar (Cash)")


class BuktiPembayaranForm(forms.Form):
    """Pelanggan memilih transfer bank / e-money, lalu mengunggah buktinya."""

    EKSTENSI_BUKTI = (".jpg", ".jpeg", ".png", ".webp", ".pdf")
    UKURAN_MAKS = 2 * 1024 * 1024

    jenis = forms.ChoiceField(choices=BuktiPembayaran.JENIS_CHOICES, widget=forms.RadioSelect,
                              label="Metode pembayaran")
    nama_penyedia = forms.CharField(max_length=50, label="Nama bank / e-money",
                                    help_text="Contoh: BRI, BCA, DANA, OVO, GoPay.")
    nomor_referensi = forms.CharField(max_length=100, label="Nomor referensi / ID transaksi",
                                      help_text="Tertera di struk transfer atau riwayat aplikasi.")
    berkas = forms.FileField(label="Bukti pembayaran",
                             help_text="Foto/tangkapan layar (JPG, PNG, WEBP) atau PDF, maksimal 2 MB.")

    def clean_berkas(self):
        berkas = self.cleaned_data["berkas"]
        if not berkas.name.lower().endswith(self.EKSTENSI_BUKTI):
            raise forms.ValidationError("Bukti harus berupa gambar JPG/PNG/WEBP atau PDF.")
        if berkas.size > self.UKURAN_MAKS:
            raise forms.ValidationError("Ukuran bukti maksimal 2 MB.")
        return berkas


class TolakBuktiForm(forms.Form):
    alasan = forms.CharField(widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}), label="Alasan penolakan")
