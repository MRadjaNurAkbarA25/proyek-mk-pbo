from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db.models import Q

from .models import Mekanik, User


class RegisterForm(UserCreationForm):
    """
    Registrasi mandiri: SELALU membuat akun dengan role PELANGGAN (FR-1).
    Sesuai desain, tidak ada kolom username: username diisi otomatis dengan e-mail.
    Alamat diisi nanti lewat halaman Profil Saya.
    """
    nama_lengkap = forms.CharField(max_length=150, label="Nama Lengkap")
    email = forms.EmailField(label="E-mail")
    no_telepon = forms.CharField(max_length=15, required=False, label="Nomor Telepon")

    class Meta:
        model = User
        fields = ["email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        isi = {
            "nama_lengkap": "Masukkan nama lengkap...",
            "email": "Masukkan alamat e-mail...",
            "no_telepon": "Masukkan nomor telepon...",
            "password1": "Masukkan kata sandi...",
            "password2": "Konfirmasi kata sandi...",
        }
        for nama, teks in isi.items():
            self.fields[nama].widget.attrs["placeholder"] = teks
        self.fields["password1"].label = "Kata Sandi"
        self.fields["password2"].label = "Konfirmasi Kata Sandi"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise forms.ValidationError("E-mail ini sudah terdaftar.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["nama_lengkap"]
        user.role = User.ROLE_PELANGGAN
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Field tetap bernama 'username', tetapi isinya boleh e-mail (lihat EmailOrUsernameBackend)."""
    username = forms.CharField(label="E-mail")
    password = forms.CharField(label="Kata Sandi", widget=forms.PasswordInput)

    def clean_username(self):
        # E-mail yang disalin-tempel sering ikut membawa spasi di depan/belakang
        # sehingga login gagal padahal datanya benar.
        return self.cleaned_data.get("username", "").strip()


class ProfilForm(forms.ModelForm):
    """Informasi pribadi pada halaman Profil Saya. Dipakai keempat role."""

    EKSTENSI_FOTO = (".jpg", ".jpeg", ".png", ".webp")

    nama_lengkap = forms.CharField(max_length=150, label="Nama Lengkap")

    class Meta:
        model = User
        fields = ["email", "no_telepon", "alamat", "jenis_kelamin", "foto"]
        labels = {
            "email": "Email",
            "no_telepon": "Nomor WhatsApp / HP",
            "alamat": "Alamat Domisili Lengkap",
            "jenis_kelamin": "Jenis Kelamin",
            "foto": "Foto Profil",
        }
        widgets = {
            "alamat": forms.Textarea(attrs={"rows": 3, "placeholder": "Insert text..."}),
            "no_telepon": forms.TextInput(attrs={"placeholder": "+628XXXXXXXXXX"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nama_lengkap"].initial = self.instance.get_full_name()
        self.fields["jenis_kelamin"].required = False
        # Alamat hanya relevan untuk role yang datang atau berangkat ke lokasi.
        self.butuh_alamat = self.instance.role in (User.ROLE_PELANGGAN, User.ROLE_MEKANIK)
        if not self.butuh_alamat:
            del self.fields["alamat"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        bentrok = User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exclude(pk=self.instance.pk)
        if bentrok.exists():
            raise forms.ValidationError("E-mail ini sudah dipakai akun lain.")
        return email

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        nama = getattr(foto, "name", "") or ""
        if foto and not nama.lower().endswith(self.EKSTENSI_FOTO):
            raise forms.ValidationError("Foto harus berformat JPG, PNG, atau WEBP.")
        if foto and getattr(foto, "size", 0) > 2 * 1024 * 1024:
            raise forms.ValidationError("Ukuran foto maksimal 2 MB.")
        return foto

    def save(self, commit=True):
        user = super().save(commit=False)
        nama = self.cleaned_data["nama_lengkap"].strip()
        user.first_name, _, user.last_name = nama.partition(" ")
        user.no_telepon = user.no_telepon.strip()
        if self.butuh_alamat:
            user.alamat = user.alamat.strip()
        if commit:
            user.save()
        return user


class KeahlianForm(forms.ModelForm):
    """Kartu tambahan khusus mekanik pada halaman Profil Saya."""

    class Meta:
        model = Mekanik
        fields = ["spesialisasi"]
        labels = {"spesialisasi": "Keahlian"}
        widgets = {
            "spesialisasi": forms.TextInput(
                attrs={"placeholder": "Contoh: Mesin, Kelistrikan, Kaki-kaki"}
            )
        }
