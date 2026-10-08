from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db.models import Q

from .models import User


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
