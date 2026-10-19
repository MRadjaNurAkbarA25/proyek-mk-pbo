from django.apps import AppConfig


class LaporanConfig(AppConfig):
    """App Laporan sesuai struktur folder di dokumen rancangan bagian 6.

    App ini sengaja tidak punya models.py: laporan tidak menyimpan data
    sendiri, melainkan membaca dari servis, pembayaran, sparepart dan
    accounts. Isinya hierarki class di laporan/laporan.py.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "laporan"
