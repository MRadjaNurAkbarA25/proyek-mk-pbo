"""Settings menolak menyala di domain publik dengan setelan laptop.

Saran reviewer: membalik nilai bawaan DEBUG menjadi 0. Alasannya benar
(kalau env server lupa diisi, situs menyala dengan DEBUG dan secret key
repo), tapi ongkosnya ditanggung empat laptop tim yang kehilangan halaman
error Django saat mengerjakan UI.

Yang dipakai sebagai gantinya: kalau DJANGO_ALLOWED_HOSTS menunjuk ke
domain sungguhan, settings menolak dimuat selama DEBUG masih menyala atau
secret key masih yang tertulis di repo. Celah yang sama tertutup, laptop
tidak terganggu.

Settings dibaca sekali saat proses Python mulai, jadi tiap kasus diuji
di proses terpisah dengan environment-nya sendiri.
"""
import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

KUNCI_SERVER = "kunci-server-panjang-0123456789abcdefghijklmnopqrstuvwxyz"


def muat_settings(**env):
    """Muat bengkel_project.settings di proses baru. Kembalikan (berhasil, pesan)."""
    lingkungan = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
    lingkungan.update(env)
    lingkungan["DJANGO_SETTINGS_MODULE"] = "bengkel_project.settings"
    hasil = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=Path(settings.BASE_DIR), env=lingkungan, capture_output=True, text=True,
    )
    return hasil.returncode == 0, hasil.stderr


class PenjagaSettingsServer(SimpleTestCase):
    def test_laptop_tanpa_env_apa_pun_tetap_jalan(self):
        ok, pesan = muat_settings()
        self.assertTrue(ok, pesan)

    def test_ip_jaringan_lokal_untuk_coba_dari_hp_tetap_jalan(self):
        ok, pesan = muat_settings(DJANGO_ALLOWED_HOSTS="localhost,192.168.1.7")
        self.assertTrue(ok, pesan)

    def test_domain_publik_dengan_debug_menyala_ditolak(self):
        ok, pesan = muat_settings(DJANGO_ALLOWED_HOSTS="bengkelsiaga.pbo.web.id",
                                  DJANGO_SECRET_KEY=KUNCI_SERVER)
        self.assertFalse(ok)
        self.assertIn("DJANGO_DEBUG", pesan)

    def test_domain_publik_dengan_secret_key_repo_ditolak(self):
        ok, pesan = muat_settings(DJANGO_ALLOWED_HOSTS="bengkelsiaga.pbo.web.id",
                                  DJANGO_DEBUG="0")
        self.assertFalse(ok)
        self.assertIn("DJANGO_SECRET_KEY", pesan)

    def test_wildcard_dianggap_publik(self):
        ok, _ = muat_settings(DJANGO_ALLOWED_HOSTS="*")
        self.assertFalse(ok)

    def test_setelan_server_yang_benar_jalan(self):
        ok, pesan = muat_settings(DJANGO_ALLOWED_HOSTS="bengkelsiaga.pbo.web.id",
                                  DJANGO_DEBUG="0", DJANGO_SECRET_KEY=KUNCI_SERVER)
        self.assertTrue(ok, pesan)
