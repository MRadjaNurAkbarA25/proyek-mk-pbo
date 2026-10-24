"""Login sosial (Facebook/Google/Apple) tidak pernah terhubung, jadi dihapus."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase

AKAR = Path(settings.BASE_DIR)


class TanpaLoginSosial(TestCase):
    def test_halaman_login_dan_daftar_tanpa_tombol_sosial(self):
        for url in ("/accounts/login/", "/accounts/register/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            for sisa in ("sosial", "facebook.png", "google.png", "apple.png", "Atau login dengan", "Atau buat akun dengan"):
                self.assertNotContains(r, sisa, msg_prefix=url)

    def test_berkas_dan_css_sosial_sudah_dihapus(self):
        for berkas in ("static/js/sosial.js", "static/images/facebook.png",
                       "static/images/google.png", "static/images/apple.png"):
            self.assertFalse((AKAR / berkas).exists(), berkas)
        css = (AKAR / "static/css/auth.css").read_text(encoding="utf-8")
        for sisa in (".sosial", ".pemisah"):
            self.assertNotIn(sisa, css)
