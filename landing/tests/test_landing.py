"""Landing page: isi fitur nyata, angka dari database, ajakan sesuai status login."""
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from landing.views import statistik_bengkel
from mekanik.models import JenisServis


class Statistik(TestCase):
    def test_angka_nol_tidak_ditampilkan(self):
        self.assertEqual(statistik_bengkel(), [])

    def test_angka_dari_database(self):
        JenisServis.objects.create(nama_servis="Ganti Oli", harga=50000, estimasi_waktu=30)
        u = User.objects.create_user(username="m", password="x", role=User.ROLE_MEKANIK)
        Mekanik.objects.create(user=u)
        nonaktif = User.objects.create_user(username="m2", password="x", role=User.ROLE_MEKANIK, is_active=False)
        Mekanik.objects.create(user=nonaktif)
        angka = {s["label"]: s["angka"] for s in statistik_bengkel()}
        self.assertEqual(angka, {"Jenis layanan": 1, "Mekanik aktif": 1})


class Halaman(TestCase):
    def test_pengunjung_diajak_mendaftar(self):
        r = self.client.get("/")
        self.assertContains(r, "Daftar dan Ajukan Servis")
        self.assertContains(r, 'href="/accounts/register/" class="chip-jenis"', count=2)
        self.assertContains(r, "Cara Kerja")
        self.assertContains(r, "https://wa.me/62")
        self.assertNotContains(r, 'id="harga"')  # belum ada jenis servis

    def test_pelanggan_langsung_ke_halaman_pelanggan(self):
        u = User.objects.create_user(username="p", password="x", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=u)
        self.client.force_login(u)
        r = self.client.get("/")
        self.assertContains(r, 'href="/pelanggan/ajukan-servis/"')
        self.assertContains(r, 'href="/pelanggan/kendaraan/tambah/motor/"')
        self.assertNotContains(r, "Daftar dan Ajukan Servis")

    def test_daftar_harga_maks_enam(self):
        for i in range(8):
            JenisServis.objects.create(nama_servis=f"Layanan {i}", harga=10000 * (i + 1), estimasi_waktu=30)
        r = self.client.get("/")
        self.assertContains(r, 'class="harga-kartu"', count=6)
        self.assertContains(r, "Rp 10.000")
        self.assertContains(r, "Dan 2 layanan lainnya.")
        self.assertNotContains(r, "Layanan 7<")
