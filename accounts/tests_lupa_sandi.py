import re

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Pelanggan, User


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
