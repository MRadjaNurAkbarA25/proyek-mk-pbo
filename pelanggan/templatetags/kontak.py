"""Filter nomor telepon untuk tombol WhatsApp dan Telepon.

Nomor di database ditulis bebas oleh penggunanya ("0812-3456-7890",
"+62 812 3456 7890", "62812..."). wa.me dan tel: butuh angka saja dalam
format internasional, jadi semuanya dirapikan ke 62xxxxxxxxxx di sini.

Pakai:
    {% load kontak %}
    <a href="https://wa.me/{{ nomor|nomor_internasional }}">WhatsApp</a>
    <a href="tel:+{{ nomor|nomor_internasional }}">Telepon</a>
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
