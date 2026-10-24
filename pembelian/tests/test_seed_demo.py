"""seed_demo: supplier dan pembelian contoh dibuat lewat method model."""
import io

from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase

from pembelian.models import DetailPembelian, PembelianSparepart, Supplier
from servis.models import DetailSparepart
from sparepart.models import Sparepart


def seed(**kw):
    call_command("seed_demo", verbosity=0, stdout=io.StringIO(), izinkan_di_server=True, **kw)


def jumlah(qs):
    return qs.aggregate(n=Sum("jumlah"))["n"] or 0


class SeedPembelian(TestCase):
    def setUp(self):
        seed()

    def test_tiga_supplier_satu_selesai_satu_draf(self):
        self.assertEqual(Supplier.objects.count(), 3)
        self.assertEqual(PembelianSparepart.objects.filter(status=PembelianSparepart.STATUS_SELESAI).count(), 1)
        self.assertEqual(PembelianSparepart.objects.filter(status=PembelianSparepart.STATUS_DRAF).count(), 1)
        for p in PembelianSparepart.objects.all():
            self.assertTrue(p.detail.exists())
            self.assertGreater(p.total, 0)

    def stok_seharusnya(self, sp, stok_awal):
        dibeli = jumlah(DetailPembelian.objects.filter(
            sparepart=sp, pembelian__status=PembelianSparepart.STATUS_SELESAI))
        dipakai = jumlah(DetailSparepart.objects.filter(sparepart=sp))
        return stok_awal + dibeli - dipakai

    def test_pembelian_selesai_menambah_stok(self):
        # Stok awal SP-004 (Busi) di seed_demo: 60. Pembelian selesai lewat
        # selesaikan() harus benar-benar menambah stok.
        busi = Sparepart.objects.get(kode="SP-004")
        self.assertTrue(DetailPembelian.objects.filter(
            sparepart=busi, pembelian__status=PembelianSparepart.STATUS_SELESAI).exists())
        self.assertEqual(busi.stok, self.stok_seharusnya(busi, 60))

    def test_reset_tidak_menghapus_stok_hasil_pembelian(self):
        seed(reset=True)
        busi = Sparepart.objects.get(kode="SP-004")
        self.assertEqual(busi.stok, self.stok_seharusnya(busi, 60))
        self.assertEqual(PembelianSparepart.objects.count(), 2)
