"""Peta hanya-lihat untuk lokasi home service: {% load peta %}{% url_embed_osm t.lokasi_lat t.lokasi_lng as src %}"""
from django import template

from bengkel_project import lokasi

register = template.Library()


@register.simple_tag
def url_embed_osm(lat, lng):
    return lokasi.url_embed_osm(lat, lng)
