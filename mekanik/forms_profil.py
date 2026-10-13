from django import forms

from accounts.models import Mekanik


class ProfilMekanikForm(forms.ModelForm):
    """Mekanik mengubah keahliannya sendiri. Status diatur lewat tombol terpisah
    supaya aturan di method Mekanik.ubah_ketersediaan() tetap berlaku."""

    class Meta:
        model = Mekanik
        fields = ["spesialisasi"]
        labels = {"spesialisasi": "Keahlian / Spesialisasi"}
        widgets = {
            "spesialisasi": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Contoh: Mesin, Kelistrikan, AC"}
            )
        }
