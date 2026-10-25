"""Format rupiah untuk semua halaman (dan teks di model).

    {% load angka %}
    {{ transaksi.total_biaya|rupiah }}   ->  Rp 1.250.000,00
"""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rupiah(nilai):
    """Titik ribuan, koma desimal, dua angka sen. Nilai kosong atau bukan angka -> 'Rp 0,00'."""
    try:
        angka = Decimal(str(nilai if nilai not in (None, "") else 0)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        angka = Decimal("0.00")
    tanda = "-" if angka < 0 else ""
    # Format Inggris "1,250,000.00" lalu tukar koma dan titik.
    teks = f"{abs(angka):,.2f}".translate(str.maketrans(",.", ".,"))
    return f"{tanda}Rp {teks}"
