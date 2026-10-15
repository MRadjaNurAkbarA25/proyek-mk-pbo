from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from accounts.models import Pelanggan, User


class PelangganCreateForm(forms.Form):
    nama_lengkap = forms.CharField(
        label="Nama Lengkap", max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="E-mail", max_length=150,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    no_telepon = forms.CharField(
        label="Nomor Telepon", max_length=15, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    alamat = forms.CharField(
        label="Alamat", required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    password1 = forms.CharField(
        label="Kata Sandi", widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="Ulangi Kata Sandi", widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise forms.ValidationError("E-mail tersebut sudah digunakan akun lain.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Konfirmasi kata sandi tidak sama.")
        if password1 and cleaned.get("email") and cleaned.get("nama_lengkap"):
            calon_user = User(
                username=cleaned["email"],
                email=cleaned["email"],
                first_name=cleaned["nama_lengkap"],
            )
            try:
                validate_password(password1, user=calon_user)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self):
        """Buat User pelanggan; pemanggil membuat profil Pelanggan dalam transaksi."""
        user = User(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            first_name=self.cleaned_data["nama_lengkap"].strip(),
            role=User.ROLE_PELANGGAN,
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()
        return user


class PelangganUpdateForm(forms.Form):
    nama_lengkap = forms.CharField(
        label="Nama Lengkap", max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="E-mail", max_length=150,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    no_telepon = forms.CharField(
        label="Nomor Telepon", max_length=15, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    alamat = forms.CharField(
        label="Alamat", required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, instance: Pelanggan, **kwargs):
        self.instance = instance
        initial = kwargs.pop("initial", {})
        initial.update({
            "nama_lengkap": instance.user.first_name or instance.user.get_full_name(),
            "email": instance.user.email,
            "no_telepon": instance.user.no_telepon,
            "alamat": instance.user.alamat,
        })
        super().__init__(*args, initial=initial, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_id = self.instance.user_id
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exclude(pk=user_id).exists():
            raise forms.ValidationError("E-mail tersebut sudah digunakan akun lain.")
        return email

    def save(self):
        user = self.instance.user
        email_lama = user.email
        email_baru = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["nama_lengkap"].strip()
        user.email = email_baru
        # Registrasi pelanggan memakai e-mail sebagai username. Jika masih sama,
        # perbarui username juga agar pelanggan tetap bisa login dengan e-mail baru.
        if user.username.casefold() == (email_lama or "").casefold():
            user.username = email_baru
        user.save(update_fields=["first_name", "email", "username"])

        user = self.instance.user
        user.no_telepon = self.cleaned_data["no_telepon"].strip()
        user.alamat = self.cleaned_data["alamat"].strip()
        user.save(update_fields=["no_telepon", "alamat"])
        return self.instance
