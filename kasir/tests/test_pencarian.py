from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Pelanggan
from kendaraan.models import Motor
from servis.models import TransaksiServis


class PencarianTransaksiTests(TestCase):
    """Kotak cari pada daftar transaksi kasir: nomor polisi, nama, kode."""

    def setUp(self):
        User = get_user_model()
        self.kasir = User.objects.create_user(username="kasir", password="demo12345", role=User.ROLE_KASIR)
        pelanggan = Pelanggan.objects.create(user=User.objects.create_user(
            username="siti", password="demo12345", role=User.ROLE_PELANGGAN, first_name="Siti"))
        motor = Motor.objects.create(
            pelanggan=pelanggan, no_polisi="KT 1234 ABC", merk="Honda",
            model_kendaraan="Vario", tahun=2021, kapasitas_mesin=110, jenis_motor="Matic")
        TransaksiServis.objects.create(
            kode_transaksi="TRX-CARI-1", status="MENUNGGU", pelanggan=pelanggan,
            kendaraan=motor, total_biaya=Decimal("100000"))
        TransaksiServis.objects.create(
            kode_transaksi="TRX-CARI-2", status="SELESAI", total_biaya=Decimal("50000"))
        self.client.force_login(self.kasir)
        self.url = reverse("kasir_transaksi_daftar")

    def test_tanpa_filter_menampilkan_semua(self):
        self.assertEqual(self.client.get(self.url).context["jumlah_hasil"], 2)

    def test_cari_nomor_polisi(self):
        respons = self.client.get(self.url, {"q": "KT 1234"})
        self.assertEqual(respons.context["jumlah_hasil"], 1)
        self.assertContains(respons, "TRX-CARI-1")

    def test_cari_nama_pelanggan(self):
        self.assertEqual(self.client.get(self.url, {"q": "Siti"}).context["jumlah_hasil"], 1)

    def test_cari_kode_transaksi(self):
        self.assertEqual(self.client.get(self.url, {"q": "TRX-CARI-2"}).context["jumlah_hasil"], 1)

    def test_cari_tidak_ketemu(self):
        self.assertEqual(self.client.get(self.url, {"q": "ZZZ"}).context["jumlah_hasil"], 0)

    def test_tanggal_ngawur_diabaikan(self):
        respons = self.client.get(self.url, {"tanggal_mulai": "bukan-tanggal"})
        self.assertEqual(respons.context["jumlah_hasil"], 2)
        self.assertEqual(respons.context["tanggal_mulai"], "")
