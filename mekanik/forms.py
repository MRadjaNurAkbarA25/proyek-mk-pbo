from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import Mekanik, User
from mekanik.models import JenisServis
from servis.models import TransaksiServis
from sparepart.models import Sparepart


KONTROL = {
    "class": "form-control"
}

PILIHAN = {
    "class": "form-select"
}

class StatusKetersediaanForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (
                Mekanik.STATUS_TERSEDIA,
                "Tersedia"
            ),
            (
                Mekanik.STATUS_CUTI,
                "Cuti"
            ),
        ],
        widget=forms.Select(
            attrs=PILIHAN
        ),
    )


class DiagnosisForm(forms.ModelForm):

    class Meta:
        model = TransaksiServis

        fields = [
            "diagnosis",
            "rekomendasi_perbaikan",
        ]

        widgets = {
            "diagnosis": forms.Textarea(
                attrs={
                    **KONTROL,
                    "rows": 3,
                }
            ),
            "rekomendasi_perbaikan": forms.Textarea(
                attrs={
                    **KONTROL,
                    "rows": 3,
                }
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(
            *args,
            **kwargs
        )

        for nama in self.fields:
            self.fields[nama].required = True


class TambahLayananForm(forms.Form):

    jenis_servis = forms.ModelChoiceField(
        queryset=JenisServis.objects.all(),
        empty_label="-- pilih layanan --",
        widget=forms.Select(
            attrs=PILIHAN
        ),
    )

    jumlah = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(
            attrs=KONTROL
        ),
    )


class TambahSparepartForm(forms.Form):

    sparepart = forms.ModelChoiceField(
        queryset=Sparepart.objects.filter(
            stok__gt=0
        ),
        empty_label="-- pilih sparepart --",
        widget=forms.Select(
            attrs=PILIHAN
        ),
    )

    jumlah = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(
            attrs=KONTROL
        ),
    )

class MekanikCreateForm(UserCreationForm):
    """
    Membuat akun User dengan role MEKANIK
    sekaligus membuat profil Mekanik.
    """

    email = forms.EmailField(
        required=False
    )

    spesialisasi = forms.CharField(
        max_length=100,
        required=False
    )

    status = forms.ChoiceField(
        choices=Mekanik.STATUS_CHOICES,
        initial=Mekanik.STATUS_TERSEDIA,
    )

    class Meta:
        model = User

        fields = [
            "username",
            "email",
        ]

    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.role = User.ROLE_MEKANIK

        user.email = (
            self.cleaned_data["email"]
        )

        if commit:
            user.save()

            Mekanik.objects.create(
                user=user,
                spesialisasi=(
                    self.cleaned_data[
                        "spesialisasi"
                    ]
                ),
                status=(
                    self.cleaned_data[
                        "status"
                    ]
                ),
            )

        return user


class MekanikUpdateForm(forms.ModelForm):

    email = forms.EmailField(
        required=False
    )

    class Meta:
        model = Mekanik

        fields = [
            "spesialisasi",
            "status",
        ]

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(
            *args,
            **kwargs
        )

        self.fields[
            "email"
        ].initial = self.instance.user.email

    def save(self, commit=True):

        mekanik = super().save(
            commit=commit
        )

        mekanik.user.email = (
            self.cleaned_data["email"]
        )

        mekanik.user.save(
            update_fields=["email"]
        )

        return mekanik