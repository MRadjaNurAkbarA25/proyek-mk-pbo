from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from accounts.models import Pelanggan
from kendaraan.models import Mobil, Motor
from servis.models import TransaksiServis


class DaftarKendaraanAdminTests(TestCase):
    """Halaman Data Kendaraan untuk admin, dan fitur hapus pelanggan yang dibuang."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="admin", password="demo12345", role=User.ROLE_ADMIN)
        self.kasir = User.objects.create_user(
            username="kasir", password="demo12345", role=User.ROLE_KASIR)
        pelanggan = Pelanggan.objects.create(user=User.objects.create_user(
            username="siti", password="demo12345", role=User.ROLE_PELANGGAN, first_name="Siti"))
        self.motor = Motor.objects.create(
            pelanggan=pelanggan, no_polisi="KT 1234 ABC", merk="Honda",
            model_kendaraan="Vario", tahun=2021, kapasitas_mesin=110, jenis_motor="Matic")
        Mobil.objects.create(
            pelanggan=pelanggan, no_polisi="KT 5678 XY", merk="Toyota",
            model_kendaraan="Avanza", tahun=2019, jumlah_pintu=5, jenis_mobil="MPV")
        TransaksiServis.objects.create(
            kode_transaksi="TRX-KEND-1", status="MENUNGGU", pelanggan=pelanggan,
            kendaraan=self.motor, total_biaya=Decimal("0"))
        self.url = reverse("kelola_kendaraan")

    def test_admin_melihat_semua_kendaraan(self):
        self.client.force_login(self.admin)
        respons = self.client.get(self.url)
        self.assertEqual(respons.context["jumlah_hasil"], 2)
        self.assertContains(respons, "KT 1234 ABC")
        self.assertContains(respons, "KT 5678 XY")

    def test_jenis_kendaraan_tampil_polimorfik(self):
        self.client.force_login(self.admin)
        isi = self.client.get(self.url).content.decode()
        self.assertIn("Motor", isi)
        self.assertIn("Mobil", isi)

    def test_cari_nomor_polisi_dan_pemilik(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url, {"q": "5678"}).context["jumlah_hasil"], 1)
        self.assertEqual(self.client.get(self.url, {"q": "Siti"}).context["jumlah_hasil"], 2)

    def test_filter_jenis(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url, {"tipe": "motor"}).context["jumlah_hasil"], 1)
        # Jenis yang tidak dikenal diabaikan, bukan bikin error.
        self.assertEqual(self.client.get(self.url, {"tipe": "pesawat"}).context["jumlah_hasil"], 2)

    def test_servis_berjalan_dihitung(self):
        self.client.force_login(self.admin)
        baris = dict((k.no_polisi, k) for k, _ in self.client.get(self.url).context["baris"])
        self.assertEqual(baris["KT 1234 ABC"].servis_aktif, 1)
        self.assertEqual(baris["KT 5678 XY"].servis_aktif, 0)

    def test_selain_admin_ditolak(self):
        self.client.force_login(self.kasir)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_rute_hapus_pelanggan_sudah_tidak_ada(self):
        with self.assertRaises(NoReverseMatch):
            reverse("kelola_pelanggan_hapus", args=[1])

    def test_daftar_pelanggan_tanpa_tombol_hapus(self):
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(reverse("kelola_pelanggan")), ">Hapus<")
