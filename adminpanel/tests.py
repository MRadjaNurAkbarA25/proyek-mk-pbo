from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Mekanik
from servis.models import TransaksiServis
from sparepart.models import Sparepart


class LaporanViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="admin", password="pass", role=User.ROLE_ADMIN, is_staff=True)
        self.other = User.objects.create_user(username="kasir", password="pass", role=User.ROLE_KASIR)
        self.mekanik = Mekanik.objects.create(user=User.objects.create_user(username="budi", password="pass", role=User.ROLE_MEKANIK))
        TransaksiServis.objects.create(kode_transaksi="TRX-1", status="SELESAI", mekanik=self.mekanik, total_biaya=Decimal("100000"))
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
        self.assertContains(response, "100000")
        self.assertNotContains(response, "150000")

    def test_stock_report_marks_low_stock(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("laporan_stok")), "STOK MINIM")

    def test_mechanic_report_aggregates_finished_work(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("laporan_mekanik"))
        self.assertContains(response, "budi")
        self.assertContains(response, "100000")
