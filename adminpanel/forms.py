from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from accounts.forms import SandiBaruOpsionalMixin
from accounts.models import Pelanggan, User
from faq.models import PertanyaanFAQ


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


class PelangganUpdateForm(SandiBaruOpsionalMixin, forms.Form):
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
        self.terapkan_sandi_baru(user)
        return self.instance

    def akun_untuk_sandi(self):
        return self.instance.user


# ----------------------------------------------------------------------
# Kelola Kasir
# ----------------------------------------------------------------------
# Kasir login dengan username; e-mail opsional (untuk Lupa Kata Sandi).

def _validasi_sandi(form, cleaned, calon_user):
    """Dua kolom sandi harus sama dan lolos validator sandi Django."""
    p1, p2 = cleaned.get("password1"), cleaned.get("password2")
    if p1 and p2 and p1 != p2:
        form.add_error("password2", "Konfirmasi kata sandi tidak sama.")
        return
    if p1:
        try:
            validate_password(p1, user=calon_user)
        except ValidationError as exc:
            form.add_error("password1", exc)


class KasirCreateForm(forms.Form):
    nama_lengkap = forms.CharField(
        label="Nama Lengkap", max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    username = forms.CharField(
        label="Username (untuk login)", max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )
    email = forms.EmailField(
        label="E-mail", max_length=150, required=False,
        help_text="Opsional. Dipakai bila kasir lupa kata sandi.",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    no_telepon = forms.CharField(
        label="Nomor Telepon", max_length=15, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    password1 = forms.CharField(
        label="Kata Sandi", widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="Ulangi Kata Sandi", widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        # Dibandingkan tanpa beda huruf besar-kecil: "Kasir1" dan "kasir1"
        # akan membingungkan saat login.
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Username tersebut sudah dipakai akun lain.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise forms.ValidationError("E-mail tersebut sudah digunakan akun lain.")
        return email

    def clean(self):
        cleaned = super().clean()
        calon = User(username=cleaned.get("username") or "", email=cleaned.get("email") or "",
                     first_name=cleaned.get("nama_lengkap") or "")
        _validasi_sandi(self, cleaned, calon)
        return cleaned

    def save(self):
        user = User(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            first_name=self.cleaned_data["nama_lengkap"].strip(),
            no_telepon=self.cleaned_data["no_telepon"].strip(),
            role=User.ROLE_KASIR,
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()
        return user


class KasirUpdateForm(SandiBaruOpsionalMixin, forms.Form):
    """Username sengaja tidak bisa diubah: itu yang dipakai kasir untuk login."""

    nama_lengkap = forms.CharField(
        label="Nama Lengkap", max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="E-mail", max_length=150, required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    no_telepon = forms.CharField(
        label="Nomor Telepon", max_length=15, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, instance: User, **kwargs):
        self.instance = instance
        initial = kwargs.pop("initial", {})
        initial.update({
            "nama_lengkap": instance.first_name or instance.get_full_name(),
            "email": instance.email,
            "no_telepon": instance.no_telepon,
        })
        super().__init__(*args, initial=initial, **kwargs)

    def akun_untuk_sandi(self):
        return self.instance

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("E-mail tersebut sudah digunakan akun lain.")
        return email

    def save(self):
        user = self.instance
        user.first_name = self.cleaned_data["nama_lengkap"].strip()
        user.email = self.cleaned_data["email"]
        user.no_telepon = self.cleaned_data["no_telepon"].strip()
        user.save(update_fields=["first_name", "email", "no_telepon"])
        self.terapkan_sandi_baru(user)
        return user

class PertanyaanFAQForm(forms.ModelForm):
    """Tambah dan ubah FAQ (FR-34). Tidak ada hapus: FAQ hanya dinonaktifkan."""

    class Meta:
        model = PertanyaanFAQ
        fields = ["kategori", "pertanyaan", "jawaban", "kata_kunci", "urutan", "aktif"]
        widgets = {
            "kategori": forms.Select(attrs={"class": "form-select"}),
            "pertanyaan": forms.TextInput(attrs={"class": "form-control"}),
            "jawaban": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "kata_kunci": forms.TextInput(attrs={"class": "form-control", "placeholder": "servis service servise"}),
            "urutan": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "aktif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {"aktif": "Tampilkan di chat (aktif)"}

    def clean_pertanyaan(self):
        return self.cleaned_data["pertanyaan"].strip()

    def clean_jawaban(self):
        jawaban = self.cleaned_data["jawaban"].strip()
        if not jawaban:
            raise forms.ValidationError("Jawaban tidak boleh kosong.")
        return jawaban

    def clean_kata_kunci(self):
        return " ".join(self.cleaned_data["kata_kunci"].split())
