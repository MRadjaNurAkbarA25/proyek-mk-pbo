import re

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import Pelanggan, User


class LupaSandiTests(TestCase):
    """Alur lupa kata sandi memakai PasswordReset bawaan Django."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="siti", password="demo12345",
            role=User.ROLE_PELANGGAN, email="siti@demo.local")
        Pelanggan.objects.create(user=self.user)

    def test_tautan_ada_di_halaman_login(self):
        self.assertContains(self.client.get(reverse("login")), reverse("password_reset"))

    def test_alur_lengkap_sampai_bisa_login_lagi(self):
        self.client.post(reverse("password_reset"), {"email": "siti@demo.local"})
        self.assertEqual(len(mail.outbox), 1)

        tautan = re.search(r"/accounts/lupa-sandi/[^/]+/[^/\s]+/", mail.outbox[0].body).group(0)
        respons = self.client.get(tautan, follow=True)
        self.assertContains(respons, "Buat Kata Sandi Baru")

        alamat = respons.redirect_chain[-1][0] if respons.redirect_chain else tautan
        self.client.post(alamat, {
            "new_password1": "Rahasia#2026", "new_password2": "Rahasia#2026",
        })
        self.assertTrue(self.client.login(username="siti", password="Rahasia#2026"))

    def test_email_tak_dikenal_tidak_membocorkan_apa_pun(self):
        """Halaman tetap mengaku berhasil, tapi tidak ada e-mail yang dikirim."""
        respons = self.client.post(reverse("password_reset"), {"email": "bukan@siapa.pun"})
        self.assertEqual(respons.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_tautan_rusak_ditolak(self):
        respons = self.client.get("/accounts/lupa-sandi/MQ/palsu-palsu/", follow=True)
        self.assertContains(respons, "Tautan Tidak Berlaku")


class LupaSandiTanpaEmailDiServer(TestCase):
    """Tanpa SMTP, halaman lupa sandi tidak boleh berpura-pura mengirim e-mail.

    Dulu di server tanpa DJANGO_EMAIL_HOST, halaman ini menulis "tautan sudah
    dikirim" padahal isinya hanya tercetak di log kontainer. Pelanggan akan
    menunggu e-mail yang tidak pernah datang.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="siti", password="demo12345",
            role=User.ROLE_PELANGGAN, email="siti@demo.local")
        Pelanggan.objects.create(user=self.user)

    def test_halaman_mengarahkan_ke_kontak_bengkel(self):
        from django.test import override_settings
        with override_settings(LUPA_SANDI_LEWAT_EMAIL=False):
            respons = self.client.get(reverse("password_reset"))
        self.assertContains(respons, "belum bisa lewat e-mail")
        self.assertContains(respons, "+62 895-0320-2323")
        self.assertNotContains(respons, 'name="email"')

    def test_kiriman_langsung_tidak_diproses(self):
        from django.test import override_settings
        with override_settings(LUPA_SANDI_LEWAT_EMAIL=False):
            respons = self.client.post(reverse("password_reset"), {"email": "siti@demo.local"})
        self.assertEqual(respons.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_server_tanpa_smtp_mematikan_jalur_email(self):
        """Nilai settings-nya sendiri, dihitung saat settings dimuat."""
        import os
        import subprocess
        import sys
        from pathlib import Path
        from django.conf import settings as s

        def nilai(**env):
            lingkungan = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
            lingkungan.update(env, DJANGO_SETTINGS_MODULE="bengkel_project.settings")
            kode = "import django; django.setup(); from django.conf import settings; print(settings.LUPA_SANDI_LEWAT_EMAIL)"
            return subprocess.run([sys.executable, "-c", kode], cwd=Path(s.BASE_DIR),
                                  env=lingkungan, capture_output=True, text=True).stdout.strip()

        server = dict(DJANGO_DEBUG="0", DJANGO_ALLOWED_HOSTS="bengkelsiaga.pbo.web.id",
                      DJANGO_SECRET_KEY="kunci-server-panjang-0123456789abcdefghijklmnop")
        self.assertEqual(nilai(), "True", "laptop: e-mail tercetak di terminal, tetap bisa diuji")
        self.assertEqual(nilai(**server), "False")
        self.assertEqual(nilai(**server, DJANGO_EMAIL_HOST="smtp.gmail.com"), "True")
