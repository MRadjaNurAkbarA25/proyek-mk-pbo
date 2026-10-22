# pelanggan/forms.py
from django import forms
from accounts.models import Mekanik, Pelanggan
from kendaraan.models import Kendaraan, Mobil, Motor
from servis.models import TransaksiServis

class KendaraanBaseForm(forms.ModelForm):
    """Kolom bersama Mobil dan Motor. Urutan dan label mengikuti desain Figma."""

    class Meta:
        model = Kendaraan
        fields = ['no_polisi', 'tahun', 'merk', 'model_kendaraan']
        labels = {
            'no_polisi': 'No Polisi',
            'tahun': 'Tahun',
            'merk': 'Merk',
            'model_kendaraan': 'Model Kendaraan',
        }
        widgets = {
            'no_polisi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cth: KT 1234 ABC', 'autocapitalize': 'characters'}),
            'tahun': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan tahun...'}),
            'merk': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan merk kendaraan...'}),
            'model_kendaraan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan model kendaraan...'}),
        }

    def clean_no_polisi(self):
        """Rapikan jadi huruf besar dengan satu spasi: 'kt  1234 abc' -> 'KT 1234 ABC'.

        Tanpa ini, 'KT 1234 ABC' dan 'kt 1234 abc' bisa terdaftar sebagai dua
        kendaraan berbeda, karena aturan unik di database membedakan huruf
        besar dan kecil.
        """
        nomor = " ".join((self.cleaned_data.get("no_polisi") or "").split()).upper()
        if not nomor:
            raise forms.ValidationError("No polisi wajib diisi.")
        lain = Kendaraan.objects.filter(no_polisi__iexact=nomor)
        if self.instance.pk:
            lain = lain.exclude(pk=self.instance.pk)
        if lain.exists():
            raise forms.ValidationError("No polisi ini sudah terdaftar.")
        return nomor

    def clean_tahun(self):
        from django.utils import timezone

        tahun = self.cleaned_data.get("tahun")
        batas = timezone.localdate().year + 1
        if tahun is not None and not 1950 <= tahun <= batas:
            raise forms.ValidationError(f"Tahun harus antara 1950 dan {batas}.")
        return tahun


class MobilForm(KendaraanBaseForm):
    class Meta(KendaraanBaseForm.Meta):
        model = Mobil
        fields = KendaraanBaseForm.Meta.fields + ['jenis_mobil', 'jumlah_pintu']
        labels = {**KendaraanBaseForm.Meta.labels, 'jenis_mobil': 'Jenis Mobil', 'jumlah_pintu': 'Jumlah Pintu'}
        widgets = {
            **KendaraanBaseForm.Meta.widgets,
            'jenis_mobil': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cth: SUV, Sedan, MPV...'}),
            'jumlah_pintu': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
        }


class MotorForm(KendaraanBaseForm):
    class Meta(KendaraanBaseForm.Meta):
        model = Motor
        fields = KendaraanBaseForm.Meta.fields + ['jenis_motor', 'kapasitas_mesin']
        labels = {**KendaraanBaseForm.Meta.labels, 'jenis_motor': 'Jenis Motor', 'kapasitas_mesin': 'Kapasitas Mesin'}
        help_texts = {'kapasitas_mesin': 'Dalam cc.'}
        widgets = {
            **KendaraanBaseForm.Meta.widgets,
            'jenis_motor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cth: Matic, Bebek, Sport...'}),
            'kapasitas_mesin': forms.NumberInput(attrs={'class': 'form-control', 'min': 50, 'placeholder': 'Cth: 125'}),
        }


class EditProfilPelangganForm(forms.ModelForm):
    """
    Tidak dipakai lagi: profil pelanggan kini ditangani accounts.ProfilForm
    pada halaman Profil Saya bersama. Disimpan agar impor lama tidak rusak.
    """

    class Meta:
        model = Pelanggan
        fields = []



class MekanikTersediaField(forms.ModelChoiceField):
    """Menampilkan nama dan spesialisasi mekanik pada pilihan Home Service."""

    def label_from_instance(self, obj):
        nama = obj.user.get_full_name().strip() or obj.user.username
        spesialisasi = obj.spesialisasi or "Umum"
        return f"{nama} — {spesialisasi} ({obj.get_status_display()})"


class HomeServiceForm(forms.Form):
    """Form pemesanan Home Service dengan kendaraan milik pelanggan yang login."""

    kendaraan = forms.ChoiceField(
        label="Kendaraan",
        choices=(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    mekanik = MekanikTersediaField(
        label="Pilih Mekanik",
        queryset=Mekanik.objects.none(),
        empty_label="-- Pilih mekanik tersedia --",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    keluhan = forms.CharField(
        label="Keluhan Kendaraan",
        min_length=5,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Jelaskan masalah kendaraan Anda...",
        }),
    )
    lokasi_servis = forms.CharField(
        label="Lokasi Home Service",
        max_length=255,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Masukkan alamat lengkap lokasi kendaraan...",
        }),
    )

    def __init__(self, *args, pelanggan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._kendaraan_by_value = {}
        pilihan_kendaraan = [("", "-- Pilih kendaraan Anda --")]

        # Penting: ambil melalui subclass Mobil/Motor agar method polymorphic
        # get_tipe() dan deskripsi_khusus() tetap tersedia.
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
                # Sama dengan form Ajukan Servis: kendaraan yang sedang punya
                # pekerjaan atau pengajuan diberi keterangan, bukan
                # disembunyikan, supaya pelanggan tahu sebelum menekan kirim.
                if TransaksiServis.alasan_kendaraan_tidak_bisa_dilayani(kendaraan):
                    label = f"{label} — sedang diproses"
                pilihan_kendaraan.append((nilai, label))
                self._kendaraan_by_value[nilai] = kendaraan

        self.fields["kendaraan"].choices = pilihan_kendaraan
        self.fields["mekanik"].queryset = Mekanik.objects.filter(
            status=Mekanik.STATUS_TERSEDIA,
            user__role="MEKANIK",
        ).select_related("user").order_by("user__first_name", "user__username")

    def clean_kendaraan(self):
        nilai = self.cleaned_data["kendaraan"]
        kendaraan = self._kendaraan_by_value.get(nilai)
        if kendaraan is None:
            raise forms.ValidationError(
                "Pilih kendaraan yang terdaftar pada akun Anda."
            )

        # Satu kendaraan hanya boleh punya satu pekerjaan berjalan. Aturannya
        # sama persis dengan form Ajukan Servis, dan memang dipanggil dari
        # tempat yang sama supaya tidak bisa berbeda. Sebelum ini form Home
        # Service tidak memeriksa apa pun, jadi kendaraan yang sedang diservis
        # masih bisa dipesankan home service berkali-kali.
        alasan = TransaksiServis.alasan_kendaraan_tidak_bisa_dilayani(kendaraan)
        if alasan:
            raise forms.ValidationError(alasan)
        return kendaraan

    def clean_keluhan(self):
        keluhan = self.cleaned_data["keluhan"].strip()
        if not keluhan:
            raise forms.ValidationError("Keluhan wajib diisi.")
        return keluhan

    def clean_lokasi_servis(self):
        lokasi = self.cleaned_data["lokasi_servis"].strip()
        if not lokasi:
            raise forms.ValidationError("Lokasi servis wajib diisi.")
        return lokasi


class PesanPelangganForm(forms.Form):
    """QoL A4: satu kalimat dari pelanggan untuk mekanik yang memegang servisnya.

    Batas panjang diambil dari field model; aturan siapa dan kapan boleh
    menulis ada di TransaksiServis.tulis_pesan_pelanggan().
    """

    keterangan = forms.CharField(
        label="Tulis pesan untuk mekanik",
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "rw-input",
            "placeholder": "Cth: Kira-kira selesai jam berapa?",
            "maxlength": 200,
        }),
    )
