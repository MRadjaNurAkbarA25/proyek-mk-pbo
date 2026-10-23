"""Uji bentuk OOP FR-35 (NFR-4), meniru gaya laporan/tests/test_hierarki.py.

Yang dikunci di sini bukan angkanya, melainkan BENTUK kodenya: abstraksi,
pewarisan, enkapsulasi, dan polimorfisme sama seperti yang dijabarkan di
dokumen perancangan.
"""
from django.test import TestCase

from laporan.laporan import SEMUA_LAPORAN, LaporanPembelian
from pembelian.models import DetailPembelian, Supplier
from sparepart.models import BarisTransaksi, DetailSparepart, Sparepart


class BentukOOPPembelianTest(TestCase):
    def test_baris_transaksi_abstrak_tanpa_tabel(self):
        """Abstraction: BarisTransaksi hanya kerangka, tidak punya tabel sendiri."""
        self.assertTrue(BarisTransaksi._meta.abstract)

    def test_kedua_detail_mewarisi_kerangka_yang_sama(self):
        """Inheritance lintas app: sparepart -> pembelian."""
        self.assertTrue(issubclass(DetailPembelian, BarisTransaksi))
        self.assertTrue(issubclass(DetailSparepart, BarisTransaksi))

    def test_subtotal_dihitung_sekali_di_induk(self):
        """Encapsulation: rumus subtotal hanya ada di BarisTransaksi."""
        self.assertEqual(BarisTransaksi.hitung_subtotal.__qualname__, "BarisTransaksi.hitung_subtotal")

    def test_detail_pembelian_tidak_menulis_ulang_rumus_subtotal(self):
        self.assertNotIn("hitung_subtotal", DetailPembelian.__dict__)
        self.assertNotIn("hitung_subtotal", DetailSparepart.__dict__)

    def test_polimorfisme_harga_satuan_berbeda_label(self):
        """Polymorphism: field yang sama, label yang berbeda sesuai konteks."""
        self.assertEqual(DetailPembelian._meta.get_field("harga_satuan").verbose_name, "Harga Beli Satuan")
        self.assertEqual(DetailSparepart._meta.get_field("harga_satuan").verbose_name, "Harga Satuan")

    def test_polimorfisme_subtotal_harga_beli_vs_jual(self):
        """Polymorphism: rumus subtotal sama, tetapi harga dasarnya beda.

        Detail pembelian menghitung subtotal harga BELI (diketik admin),
        DetailSparepart menghitung subtotal harga JUAL master sparepart.
        """
        sp = Sparepart.objects.create(
            kode="OOP-1", nama="Oli Mesin", kategori="Oli",
            harga=55000, stok=10, stok_minimum=5,
        )
        beli = DetailPembelian(sparepart=sp, jumlah=2, harga_satuan=40000)
        jual = DetailSparepart(sparepart=sp, jumlah=2, harga_satuan=sp.harga)
        self.assertEqual(beli.hitung_subtotal(), 80000)
        self.assertEqual(jual.hitung_subtotal(), 110000)

    def test_supplier_rule_status_hanya_lewat_method(self):
        """Encapsulation: status aktif diubah lewat method, bukan field langsung."""
        s = Supplier.objects.create(nama="CV Abadi")
        s.nonaktifkan()
        self.assertFalse(Supplier.objects.get(pk=s.pk).aktif)
        s.aktifkan()
        self.assertTrue(Supplier.objects.get(pk=s.pk).aktif)

    def test_laporan_pembelian_turunan_kelima_laporan(self):
        """Polymorphism: LaporanPembelian bergabung di SEMUA_LAPORAN."""
        self.assertIn(LaporanPembelian, SEMUA_LAPORAN)