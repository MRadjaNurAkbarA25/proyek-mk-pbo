"""Filter nomor telepon ke format 62xxxxxxxxxx untuk wa.me dan tel:.

Pakai: {{ nomor|nomor_internasional }}
"""
from django import template

register = template.Library()


@register.filter
def nomor_internasional(nomor):
    """'0812-3456-7890' / '+62 812 3456 7890' -> '6281234567890'. Kosong bila tidak ada angka."""
    angka = "".join(c for c in str(nomor or "") if c.isdigit())
    if angka.startswith("0"):
        return "62" + angka[1:]
    if angka.startswith("8"):
        return "62" + angka
    return angka
