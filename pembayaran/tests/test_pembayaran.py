from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Pelanggan
from servis.models import TransaksiServis

from pembayaran.models import Pembayaran


class AksesNotaTests(TestCase):
    """Nota boleh dibuka kasir, admin, dan pemilik transaksinya sendiri (FR-25)."""

    def setUp(self):
        User = get_user_model()
        self.pemilik = Pelanggan.objects.create(user=User.objects.create_user(
            username="siti", password="demo12345", role=User.ROLE_PELANGGAN))
        self.lain = Pelanggan.objects.create(user=User.objects.create_user(
            username="joko", password="demo12345", role=User.ROLE_PELANGGAN))
        self.kasir = User.objects.create_user(username="kasir", password="demo12345", role=User.ROLE_KASIR)
        self.admin = User.objects.create_user(username="admin", password="demo12345", role=User.ROLE_ADMIN)
        self.mekanik = User.objects.create_user(username="budi", password="demo12345", role=User.ROLE_MEKANIK)

        transaksi = TransaksiServis.objects.create(
            kode_transaksi="TRX-NOTA-1", status="SELESAI",
            pelanggan=self.pemilik, total_biaya=Decimal("150000"))
        self.pembayaran = Pembayaran.buat(
            transaksi, Pembayaran.METODE_CASH, uang_dibayar=Decimal("150000"))
        self.url = reverse("pembayaran_nota", args=[self.pembayaran.pk])

    def test_pemilik_bisa_membuka_notanya(self):
        self.client.force_login(self.pemilik.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_pelanggan_lain_ditolak(self):
        self.client.force_login(self.lain.user)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_kasir_dan_admin_bisa_membuka(self):
        for user in (self.kasir, self.admin):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 200, user.role)

    def test_mekanik_ditolak(self):
        self.client.force_login(self.mekanik)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_anonim_ditolak(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
