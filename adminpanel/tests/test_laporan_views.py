from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Mekanik
from pembayaran.models import Pembayaran
from servis.models import TransaksiServis
from sparepart.models import Sparepart


class LaporanViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="admin", password="pass", role=User.ROLE_ADMIN, is_staff=True)
        self.other = User.objects.create_user(username="kasir", password="pass", role=User.ROLE_KASIR)
        self.kasir_staff = User.objects.create_user(username="kasir_staff", password="pass", role=User.ROLE_KASIR, is_staff=True)
        self.mekanik = Mekanik.objects.create(user=User.objects.create_user(username="budi", password="pass", role=User.ROLE_MEKANIK))
        self.mekanik_baru = Mekanik.objects.create(user=User.objects.create_user(username="sari", password="pass", role=User.ROLE_MEKANIK))
        self.selesai = TransaksiServis.objects.create(kode_transaksi="TRX-1", status="SELESAI", mekanik=self.mekanik, total_biaya=Decimal("100000"))
        TransaksiServis.objects.create(kode_transaksi="TRX-2", status="MENUNGGU", total_biaya=Decimal("50000"))
        Sparepart.objects.create(kode="SP-1", nama="Oli", kategori="Pelumas", harga=Decimal("50000"), stok=2, stok_minimum=5)

    def test_non_admin_forbidden(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("laporan_transaksi")).status_code, 302)

    def test_transaction_report_filters_status(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("laporan_transaksi"), {"status": "SELESAI"})
        self.assertContains(response, "TRX-1")
        self.assertNotContains(response, "TRX-2")

    def test_revenue_only_counts_finished_transactions(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("laporan_pendapatan"))
        self.assertContains(response, "Rp 100.000,00")
        self.assertNotContains(response, "Rp 150.000,00")

    def test_stock_report_marks_low_stock(self):
        # Label badge sekarang berasal dari Sparepart.label_stok lewat partial
        # sparepart/_badge_stok.html, dan tulisannya "Stok Minim" (bukan huruf
        # besar semua) supaya seragam dengan daftar sparepart dan peringatan
        # stok. Yang diuji tetap sama: stok di bawah minimum ditandai.
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("laporan_stok")), "Stok Minim")

    def test_mechanic_report_aggregates_finished_work(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("laporan_mekanik"))
        self.assertContains(response, "budi")
        self.assertContains(response, "Rp 100.000,00")

    # ---- tambahan perbaikan ----

    def test_kasir_berstatus_staff_tetap_ditolak(self):
        """is_staff bukan penanda Admin: kasir yang is_staff=True tidak boleh membuka laporan."""
        self.client.force_login(self.kasir_staff)
        for nama in ("laporan_transaksi", "laporan_pendapatan", "laporan_stok", "laporan_mekanik"):
            self.assertEqual(self.client.get(reverse(nama)).status_code, 302, nama)

    def test_pendapatan_diterima_dihitung_dari_pembayaran(self):
        """Transaksi selesai yang belum dibayar tidak boleh dihitung sebagai uang masuk."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("laporan_pendapatan"))
        self.assertEqual(response.context["total_dibayar"], Decimal("0"))
        self.assertEqual(response.context["jumlah_belum_dibayar"], 1)

        Pembayaran.buat(self.selesai, Pembayaran.METODE_CASH, uang_dibayar=Decimal("100000"))
        response = self.client.get(reverse("laporan_pendapatan"))
        self.assertEqual(response.context["total_dibayar"], Decimal("100000"))
        self.assertEqual(response.context["jumlah_belum_dibayar"], 0)
        self.assertContains(response, "Cash")

    def test_mekanik_tanpa_servis_tetap_muncul(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("laporan_mekanik")), "sari")
