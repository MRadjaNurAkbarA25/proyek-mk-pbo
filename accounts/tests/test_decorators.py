"""Satu sumber untuk pembatasan halaman per role.

Dulu ada tiga salinan: role_required di accounts, admin_required di app
mekanik (tempat yang keliru), dan pelanggan_required di app pelanggan.
Sekarang semuanya di accounts/decorators.py.

Perbedaan perilaku superuser sengaja dipertahankan, tapi kini tersurat:
superuser boleh membuka halaman admin, kasir, dan sparepart, tapi TIDAK
halaman pelanggan dan mekanik, karena halaman-halaman itu membaca profil
pelanggan/mekanik milik akun yang login, dan superuser tidak punya profil
itu. Tanpa pembatasan ini halamannya error 500.
"""
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User


class DecoratorRole(TestCase):
    def setUp(self):
        self.su = User.objects.create_superuser(username="akar", password="x", email="")
        self.su.role = ""
        self.su.save()
        self.kasir = User.objects.create_user(username="kasir9", password="x", role=User.ROLE_KASIR)
        self.mek = User.objects.create_user(username="mek9", password="x", role=User.ROLE_MEKANIK)
        self.pel = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=self.pel)

    def buka(self, akun, url):
        self.client.force_login(akun)
        return self.client.get(url)

    def test_belum_login_diarahkan_ke_login(self):
        for url in ("/adminpanel/dashboard/", "/pelanggan/dashboard/", "/mekanik/dashboard/"):
            respons = self.client.get(url)
            self.assertEqual(respons.status_code, 302, url)
            self.assertIn("/accounts/login/", respons.url, url)

    def test_superuser_boleh_halaman_admin_dan_kelola_mekanik(self):
        self.assertEqual(self.buka(self.su, "/adminpanel/dashboard/").status_code, 200)
        self.assertEqual(self.buka(self.su, "/mekanik/kelola/").status_code, 200)

    def test_superuser_ditolak_rapi_di_halaman_pelanggan_dan_mekanik(self):
        """Ditolak dengan redirect, bukan error 500 karena profilnya tidak ada."""
        for url in ("/pelanggan/dashboard/", "/pelanggan/riwayat/", "/mekanik/dashboard/"):
            respons = self.buka(self.su, url)
            self.assertEqual(respons.status_code, 302, url)

    def test_kasir_ditolak_di_halaman_admin_dengan_pesan_jelas(self):
        respons = self.client.get("/adminpanel/dashboard/")  # belum login
        self.client.force_login(self.kasir)
        respons = self.client.get("/mekanik/kelola/", follow=True)
        self.assertContains(respons, "khusus untuk Admin")

    def test_mekanik_mendapat_profil_otomatis(self):
        self.assertFalse(Mekanik.objects.filter(user=self.mek).exists())
        self.assertEqual(self.buka(self.mek, "/mekanik/dashboard/").status_code, 200)
        self.assertTrue(Mekanik.objects.filter(user=self.mek).exists())

    def test_hanya_satu_sumber_decorator(self):
        import importlib.util
        for nama in ("mekanik.decorators", "pelanggan.decorators"):
            self.assertIsNone(importlib.util.find_spec(nama), f"{nama} seharusnya sudah dihapus")
