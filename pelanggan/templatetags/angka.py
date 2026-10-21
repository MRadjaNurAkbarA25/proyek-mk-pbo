"""Format angka untuk halaman pelanggan.

    {% load angka %}
    {{ transaksi.total_biaya|rupiah }}   ->  Rp 1.250.000
"""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rupiah(nilai):
    """Rupiah bulat dengan titik ribuan. Nilai kosong atau bukan angka -> 'Rp 0'."""
    try:
        bulat = int(Decimal(str(nilai if nilai not in (None, "") else 0)).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        bulat = 0
    tanda = "-" if bulat < 0 else ""
    return f"{tanda}Rp {abs(bulat):,}".replace(",", ".")
