"""Hierarki Laporan: yang diuji bentuk OOP-nya, bukan angkanya.

Angka tiap laporan sudah dijaga adminpanel/tests.py lewat halamannya.
Di sini yang dikunci justru hal yang membuat dokumen bagian 5E benar:
Laporan memang abstrak, turunannya memang empat, dan keempatnya memang
bisa diperlakukan sama.
"""
from django.test import RequestFactory, TestCase

from laporan.laporan import (
    SEMUA_LAPORAN, Laporan, LaporanMekanik, LaporanPembelian, LaporanPendapatan,
    LaporanServis, LaporanStok,
)


class HierarkiLaporanTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

    def test_laporan_tidak_bisa_dibuat_objeknya(self):
        """Abstraction: Laporan hanya kerangka, bukan laporan yang berdiri sendiri."""
        with self.assertRaises(TypeError):
            Laporan(self.request)

    def test_turunan_tanpa_ambil_data_juga_ditolak(self):
        class LaporanSetengahJadi(Laporan):
            pass

        with self.assertRaises(TypeError):
            LaporanSetengahJadi(self.request)

    def test_keempat_turunan_mewarisi_laporan(self):
        for kelas in SEMUA_LAPORAN:
            self.assertTrue(issubclass(kelas, Laporan), kelas.__name__)

    def test_polimorfisme_konteks_dipanggil_seragam(self):
        """Satu baris yang sama jalan untuk seluruh laporan, hasilnya beda-beda."""
        judul = set()
        for kelas in SEMUA_LAPORAN:
            konteks = kelas(self.request).konteks()
            self.assertIsInstance(konteks, dict, kelas.__name__)
            self.assertTrue(konteks, f"{kelas.__name__} mengembalikan konteks kosong")
            judul.add(kelas.judul)
        self.assertEqual(len(judul), len(SEMUA_LAPORAN), "tiap laporan harus punya judulnya sendiri")

    def test_rentang_tanggal_diwarisi_bukan_ditulis_ulang(self):
        """Encapsulation: hanya induk yang tahu cara membaca rentang tanggal."""
        for kelas in SEMUA_LAPORAN:
            self.assertNotIn(
                "_saring_tanggal", kelas.__dict__,
                f"{kelas.__name__} menulis ulang penyaringan tanggal",
            )

    def test_laporan_stok_tidak_memakai_rentang_tanggal(self):
        self.assertFalse(LaporanStok.pakai_rentang_tanggal)
        konteks = LaporanStok(self.request).konteks()
        self.assertNotIn("tanggal_mulai", konteks)

    def test_laporan_bertanggal_mengirim_rentangnya_ke_template(self):
        for kelas in (LaporanServis, LaporanPendapatan, LaporanMekanik):
            konteks = kelas(self.request).konteks()
            self.assertIn("tanggal_mulai", konteks, kelas.__name__)
            self.assertIn("tanggal_selesai", konteks, kelas.__name__)
