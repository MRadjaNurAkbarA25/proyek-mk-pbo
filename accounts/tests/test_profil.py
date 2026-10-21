from django.test import TestCase
from django.urls import reverse

from accounts.models import Mekanik, Pelanggan, User


class ProfilSayaTests(TestCase):
    """Halaman Profil Saya dipakai bersama keempat role (lihat accounts.views)."""

    def setUp(self):
        self.pelanggan = User.objects.create_user(
            username="siti", password="demo12345", role=User.ROLE_PELANGGAN, email="siti@demo.local")
        Pelanggan.objects.create(user=self.pelanggan)
        self.mekanik_user = User.objects.create_user(
            username="budi", password="demo12345", role=User.ROLE_MEKANIK, email="budi@demo.local")
        self.mekanik = Mekanik.objects.create(user=self.mekanik_user)
        self.kasir = User.objects.create_user(
            username="kasir", password="demo12345", role=User.ROLE_KASIR, email="kasir@demo.local")
        self.admin = User.objects.create_user(
            username="admin", password="demo12345", role=User.ROLE_ADMIN, email="admin@demo.local")

    def test_wajib_login(self):
        self.assertEqual(self.client.get(reverse("profil_saya")).status_code, 302)

    def test_keempat_role_bisa_membuka(self):
        for user in (self.pelanggan, self.mekanik_user, self.kasir, self.admin):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("profil_saya")).status_code, 200, user.role)

    def test_alamat_hanya_untuk_pelanggan_dan_mekanik(self):
        for user, ada in ((self.pelanggan, True), (self.mekanik_user, True),
                          (self.kasir, False), (self.admin, False)):
            self.client.force_login(user)
            isi = self.client.get(reverse("profil_saya")).content.decode()
            self.assertEqual("Alamat Domisili" in isi, ada, user.role)

    def test_keahlian_hanya_untuk_mekanik(self):
        self.client.force_login(self.mekanik_user)
        self.assertContains(self.client.get(reverse("profil_saya")), "Keahlian")
        self.client.force_login(self.pelanggan)
        self.assertNotContains(self.client.get(reverse("profil_saya")), "Keahlian &amp; Status")

    def test_simpan_profil_merapikan_spasi(self):
        self.client.force_login(self.pelanggan)
        self.client.post(reverse("profil_saya"), {
            "aksi": "profil", "nama_lengkap": "Siti Aminah", "email": "siti@demo.local",
            "no_telepon": "  08123456789  ", "alamat": "  Jl. Mawar 10  ", "jenis_kelamin": "P",
        })
        self.pelanggan.refresh_from_db()
        self.assertEqual(self.pelanggan.no_telepon, "08123456789")
        self.assertEqual(self.pelanggan.alamat, "Jl. Mawar 10")
        self.assertTrue(self.pelanggan.profil_lengkap)

    def test_email_bentrok_ditolak(self):
        self.client.force_login(self.pelanggan)
        respons = self.client.post(reverse("profil_saya"), {
            "aksi": "profil", "nama_lengkap": "Siti", "email": "budi@demo.local",
            "no_telepon": "08", "alamat": "a", "jenis_kelamin": "",
        })
        self.assertContains(respons, "sudah dipakai akun lain")
        self.pelanggan.refresh_from_db()
        self.assertEqual(self.pelanggan.email, "siti@demo.local")

    def test_mekanik_menyimpan_keahlian_sekaligus(self):
        self.client.force_login(self.mekanik_user)
        self.client.post(reverse("profil_saya"), {
            "aksi": "profil", "nama_lengkap": "Budi", "email": "budi@demo.local",
            "no_telepon": "0812", "alamat": "Jl. Melati", "jenis_kelamin": "L",
            "spesialisasi": "Kelistrikan",
        })
        self.mekanik.refresh_from_db()
        self.assertEqual(self.mekanik.spesialisasi, "Kelistrikan")

    def test_ganti_sandi_tidak_membuat_logout(self):
        self.client.force_login(self.pelanggan)
        respons = self.client.post(reverse("profil_saya"), {
            "aksi": "sandi", "old_password": "demo12345",
            "new_password1": "Rahasia#2026", "new_password2": "Rahasia#2026",
        }, follow=True)
        self.assertTrue(respons.context["user"].is_authenticated)
        self.assertTrue(self.client.login(username="siti", password="Rahasia#2026"))

    def test_sandi_lama_salah_ditolak(self):
        self.client.force_login(self.pelanggan)
        self.client.post(reverse("profil_saya"), {
            "aksi": "sandi", "old_password": "salah",
            "new_password1": "Rahasia#2026", "new_password2": "Rahasia#2026",
        })
        self.assertTrue(self.client.login(username="siti", password="demo12345"))

    def test_pop_up_muncul_sesudah_ganti_sandi(self):
        self.client.force_login(self.pelanggan)
        respons = self.client.post(reverse("profil_saya"), {
            "aksi": "sandi", "old_password": "demo12345",
            "new_password1": "Rahasia#2026", "new_password2": "Rahasia#2026",
        })
        self.assertEqual(respons["Location"], reverse("profil_saya") + "?sandi=ok")
        self.assertContains(self.client.get(respons["Location"]), "popupSukses")
        # Tanpa penanda di URL, pop up tidak boleh muncul lagi.
        self.assertNotContains(self.client.get(reverse("profil_saya")), "popupSukses")

    def test_url_profil_lama_dialihkan(self):
        self.client.force_login(self.pelanggan)
        self.assertRedirects(self.client.get(reverse("edit_profil")), reverse("profil_saya"))
        self.client.force_login(self.mekanik_user)
        self.assertRedirects(self.client.get(reverse("mekanik_profil")), reverse("profil_saya"))


class KeamananAntarmukaTests(TestCase):
    """Tombol lihat sandi dan konfirmasi sebelum keluar."""

    def setUp(self):
        self.pelanggan = User.objects.create_user(
            username="siti", password="demo12345", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=self.pelanggan)

    def test_tombol_lihat_sandi_ada_di_login_dan_register(self):
        self.assertContains(self.client.get(reverse("login")), "data-lihat-sandi", count=1)
        # Halaman buat akun punya dua kolom sandi, jadi dua tombol.
        self.assertContains(self.client.get(reverse("register")), "data-lihat-sandi", count=2)

    def test_tombol_keluar_meminta_konfirmasi(self):
        self.client.force_login(self.pelanggan)
        self.assertContains(self.client.get(reverse("pelanggan_dashboard")), "data-konfirmasi")

    def test_logout_lewat_get_tidak_mengeluarkan(self):
        self.client.force_login(self.pelanggan)
        self.client.get(reverse("logout"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_lewat_post_mengeluarkan(self):
        self.client.force_login(self.pelanggan)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
