from django.apps import AppConfig


class LaporanConfig(AppConfig):
    """App Laporan tanpa models.py: hierarki class di laporan/laporan.py membaca data app lain."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "laporan"
