from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Mekanik, Pelanggan
from kendaraan.models import Motor
from pembayaran.models import Pembayaran
from servis.models import TransaksiServis


class NamaTampilBukanUsername(TestCase):
    """Halaman transaksi menyebut pelanggan dan mekanik dengan namanya,
    bukan username login (pelanggan1, mekanik2)."""

    def setUp(self):
        User = get_user_model()
        self.pelanggan = Pelanggan.objects.create(user=User.objects.create_user(
            username="akunpelangganx", password="demo12345", role=User.ROLE_PELANGGAN,
            first_name="Siti", last_name="Aminah"))
        self.mekanik = Mekanik.objects.create(user=User.objects.create_user(
            username="akunmekanikx", password="demo12345", role=User.ROLE_MEKANIK,
            first_name="Budi", last_name="Santoso"))
        motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 7788 NM", merk="Honda",
            model_kendaraan="Vario", tahun=2021, kapasitas_mesin=110, jenis_motor="Matic")
        self.transaksi = TransaksiServis.objects.create(
            kode_transaksi="TRX-NAMA-1", status="SELESAI", pelanggan=self.pelanggan,
            mekanik=self.mekanik, kendaraan=motor, total_biaya=Decimal("150000"))
        self.kasir = User.objects.create_user(username="kasir", password="demo12345", role=User.ROLE_KASIR)
        self.admin = User.objects.create_user(username="admin", password="demo12345", role=User.ROLE_ADMIN)

    def periksa(self, respons, *nama):
        self.assertEqual(respons.status_code, 200)
        for n in nama:
            self.assertContains(respons, n)
        self.assertNotContains(respons, "akunpelangganx")
        self.assertNotContains(respons, "akunmekanikx")

    def test_daftar_transaksi_kasir(self):
        self.client.force_login(self.kasir)
        self.periksa(self.client.get(reverse("kasir_transaksi_daftar")), "Siti Aminah")

    def test_detail_transaksi_kasir(self):
        self.client.force_login(self.kasir)
        respons = self.client.get(reverse("kasir_transaksi_detail", args=[self.transaksi.pk]))
        self.periksa(respons, "Siti Aminah", "Budi Santoso")

    def test_nota(self):
        pembayaran = Pembayaran.buat(self.transaksi, Pembayaran.METODE_CASH, uang_dibayar=Decimal("150000"))
        self.client.force_login(self.kasir)
        self.periksa(self.client.get(reverse("pembayaran_nota", args=[pembayaran.pk])), "Siti Aminah")

    def test_laporan_transaksi(self):
        self.client.force_login(self.admin)
        self.periksa(self.client.get(reverse("laporan_transaksi")), "Budi Santoso")
