"""FR-31: form pelanggan untuk mengajukan servis di bengkel ke kasir."""

from django import forms
from django.utils import timezone

from kendaraan.models import Kendaraan
from servis.models import PengajuanServis


class PengajuanServisForm(forms.Form):
    """Pilihan kendaraan dibatasi pada kendaraan milik pelanggan yang login."""

    kendaraan = forms.ChoiceField(
        label="Kendaraan yang akan diservis",
        choices=(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    keluhan = forms.CharField(
        label="Keluhan kendaraan",
        min_length=5,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Contoh: mesin terasa bergetar saat jalan di atas 60 km/jam.",
        }),
        help_text="Tulis sejelas mungkin supaya mekanik punya gambaran awal.",
    )
    tanggal_rencana_datang = forms.DateField(
        label="Rencana datang ke bengkel",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        help_text="Boleh dikosongkan kalau belum pasti.",
    )

    def __init__(self, *args, pelanggan=None, kendaraan_awal=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pelanggan = pelanggan
        self._kendaraan_by_value = {}
        pilihan = [("", "-- Pilih kendaraan Anda --")]

        # Diambil lewat subclass Mobil/Motor, bukan Kendaraan, supaya
        # get_tipe() dan deskripsi_khusus() tetap polimorfis pada label pilihan.
        for model in Kendaraan.model_subkelas():
            queryset = model.objects.all()
            if pelanggan is not None:
                queryset = queryset.filter(pelanggan=pelanggan)
            for kendaraan in queryset.order_by("merk", "model_kendaraan"):
                nilai = f"{model.__name__.lower()}:{kendaraan.pk}"
                label = (
                    f"{kendaraan.get_tipe()} — {kendaraan.merk} "
                    f"{kendaraan.model_kendaraan} ({kendaraan.no_polisi})"
                )
                # Kendaraan yang sedang diservis atau sudah diajukan diberi
                # keterangan, bukan disembunyikan, supaya pelanggan paham kenapa.
                alasan = PengajuanServis.alasan_kendaraan_tidak_bisa(kendaraan)
                if alasan:
                    label = f"{label} — sedang diproses"
                pilihan.append((nilai, label))
                self._kendaraan_by_value[nilai] = kendaraan

        self.fields["kendaraan"].choices = pilihan

        # ?kendaraan=<pk> dari kartu pengingat servis. Hanya dicocokkan ke
        # pilihan di atas, jadi kendaraan milik orang lain tidak pernah terpilih.
        if kendaraan_awal and not self.is_bound:
            for nilai in self._kendaraan_by_value:
                if nilai.endswith(f":{kendaraan_awal}"):
                    self.initial["kendaraan"] = nilai
                    break

    @property
    def ada_kendaraan(self):
        return bool(self._kendaraan_by_value)

    def clean_kendaraan(self):
        nilai = self.cleaned_data["kendaraan"]
        kendaraan = self._kendaraan_by_value.get(nilai)
        if kendaraan is None:
            raise forms.ValidationError(
                "Pilih kendaraan yang terdaftar pada akun Anda."
            )
        alasan = PengajuanServis.alasan_kendaraan_tidak_bisa(kendaraan)
        if alasan:
            raise forms.ValidationError(alasan)
        return kendaraan

    def clean_keluhan(self):
        keluhan = self.cleaned_data["keluhan"].strip()
        if not keluhan:
            raise forms.ValidationError("Keluhan wajib diisi.")
        return keluhan

    def clean_tanggal_rencana_datang(self):
        tanggal = self.cleaned_data.get("tanggal_rencana_datang")
        if tanggal and tanggal < timezone.localdate():
            raise forms.ValidationError("Tanggal rencana datang tidak boleh di masa lalu.")
        return tanggal


class TanggalDatangForm(forms.Form):
    """Ubah rencana tanggal datang, untuk pengajuan yang belum ditinjau maupun transaksi yang belum tiba."""

    tanggal_rencana_datang = forms.DateField(
        label="Rencana datang ke bengkel",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        help_text="Kosongkan kalau belum bisa dipastikan.",
    )

    def clean_tanggal_rencana_datang(self):
        tanggal = self.cleaned_data.get("tanggal_rencana_datang")
        if tanggal and tanggal < timezone.localdate():
            raise forms.ValidationError("Tanggal rencana datang tidak boleh di masa lalu.")
        return tanggal


class TolakPengajuanForm(forms.Form):
    """Kasir wajib menuliskan alasan saat menolak, supaya pelanggan tahu sebabnya."""

    alasan = forms.CharField(
        label="Alasan penolakan",
        min_length=5,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Contoh: bengkel penuh sampai akhir pekan, silakan ajukan ulang hari Senin.",
        }),
    )

    def clean_alasan(self):
        alasan = self.cleaned_data["alasan"].strip()
        if not alasan:
            raise forms.ValidationError("Alasan penolakan wajib diisi.")
        return alasan
