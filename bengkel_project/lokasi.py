"""Titik koordinat dari peta (OpenStreetMap) dan tautan Google Maps, dipakai form dan model."""
import math
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlencode

from django import forms

# Kira-kira wilayah Indonesia; titik di luar ini dianggap salah klik dan diabaikan.
BATAS_LAT = (-11, 6)
BATAS_LNG = (95, 141)
ENAM_DESIMAL = Decimal("0.000001")


def titik_dari(lat, lng):
    """(lat, lng) sebagai Decimal 6 desimal, atau (None, None) kalau kosong, bukan angka, atau di luar Indonesia."""
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return None, None
    if not (math.isfinite(lat) and math.isfinite(lng)):
        return None, None
    if not (BATAS_LAT[0] <= lat <= BATAS_LAT[1] and BATAS_LNG[0] <= lng <= BATAS_LNG[1]):
        return None, None
    bulat = lambda x: Decimal(repr(x)).quantize(ENAM_DESIMAL, rounding=ROUND_HALF_UP)
    return bulat(lat), bulat(lng)


def url_google_maps(lat=None, lng=None, alamat=""):
    """Tautan pencarian Google Maps ke titik, atau ke alamat kalau titiknya tidak ada."""
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    if alamat:
        return "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": alamat})
    return None


def url_embed_osm(lat, lng, jarak=0.004):
    """Peta OpenStreetMap kecil (iframe) berpusat di titik, dengan satu pin."""
    lat, lng = float(lat), float(lng)
    kotak = f"{lng - jarak},{lat - jarak},{lng + jarak},{lat + jarak}"
    return ("https://www.openstreetmap.org/export/embed.html?"
            + urlencode({"bbox": kotak, "layer": "mapnik", "marker": f"{lat},{lng}"}))


class IsianTitikMixin:
    """Dua isian tersembunyi lat/lng untuk form yang memakai peta; titik tidak sah jadi None tanpa menggagalkan form."""

    nama_titik = ("lat", "lng")

    def tambah_isian_titik(self, awal=(None, None)):
        for nama, nilai in zip(self.nama_titik, awal):
            self.fields[nama] = forms.CharField(required=False, widget=forms.HiddenInput, initial=nilai)

    def clean(self):
        data = super().clean()
        lat, lng = self.nama_titik
        if lat in self.fields:
            data[lat], data[lng] = titik_dari(data.get(lat), data.get(lng))
        return data
