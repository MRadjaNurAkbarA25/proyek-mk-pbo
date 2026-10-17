"""Uji aturan model PengajuanServis (FR-31).

Yang diuji di sini adalah perilaku objeknya, bukan halamannya: aturan kapan
pengajuan boleh dibuat, apa yang terjadi saat diterima atau ditolak, dan
apakah status yang sudah final benar-benar tidak bisa diubah lagi.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis


class PengajuanServisTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pel_uji", password="rahasia123", role=User.ROLE_PELANGGAN
        )
        self.pelanggan = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(
            username="kasir_uji", password="rahasia123", role=User.ROLE_KASIR
        )
        self.kendaraan = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1 UJI", merk="Honda",
            model_kendaraan="Beat", tahun=2021, jenis_motor="Matic",
            kapasitas_mesin=110,
        )

    def _pengajuan(self, kendaraan=None):
        return PengajuanServis.objects.create(
            pelanggan=self.pelanggan,
            kendaraan=kendaraan or self.kendaraan,
            keluhan="Rem belakang bunyi",
        )

    # ---------- status awal ----------

    def test_pengajuan_baru_berstatus_menunggu(self):
        pengajuan = self._pengajuan()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_MENUNGGU)
        self.assertTrue(pengajuan.masih_menunggu)
        self.assertIsNone(pengajuan.transaksi)

    # ---------- terima ----------

    def test_terima_membuat_transaksi_di_bengkel_yang_masuk_antrian(self):
        pengajuan = self._pengajuan()
        transaksi = pengajuan.terima(self.kasir)

        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DITERIMA)
        self.assertEqual(pengajuan.transaksi, transaksi)
        self.assertEqual(pengajuan.diproses_oleh, self.kasir)
        self.assertIsNotNone(pengajuan.diproses_pada)

        # Transaksi hasil pengajuan harus bisa diambil mekanik dari antrian:
        # belum ada mekanik, tipe di bengkel, status menunggu.
        self.assertIsNone(transaksi.mekanik)
        self.assertEqual(transaksi.tipe_layanan, TransaksiServis.TIPE_DI_BENGKEL)
        self.assertEqual(transaksi.status, TransaksiServis.STATUS_MENUNGGU)
        self.assertTrue(transaksi.kode_transaksi.startswith("TRX-"))
        self.assertEqual(transaksi.keluhan, pengajuan.keluhan)

    def test_terima_dua_kali_ditolak_dan_tidak_membuat_transaksi_ganda(self):
        pengajuan = self._pengajuan()
        pengajuan.terima(self.kasir)

        with self.assertRaises(ValidationError):
            pengajuan.terima(self.kasir)
        self.assertEqual(TransaksiServis.objects.count(), 1)

    # ---------- tolak ----------

    def test_tolak_menyimpan_alasan_dan_tidak_membuat_transaksi(self):
        pengajuan = self._pengajuan()
        pengajuan.tolak(self.kasir, "  Bengkel penuh sampai Senin.  ")

        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DITOLAK)
        self.assertEqual(pengajuan.catatan_kasir, "Bengkel penuh sampai Senin.")
        self.assertEqual(TransaksiServis.objects.count(), 0)

    def test_tolak_tanpa_alasan_ditolak(self):
        pengajuan = self._pengajuan()
        with self.assertRaises(ValidationError):
            pengajuan.tolak(self.kasir, "   ")
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_MENUNGGU)

    def test_tidak_bisa_terima_setelah_ditolak(self):
        pengajuan = self._pengajuan()
        pengajuan.tolak(self.kasir, "Bengkel penuh.")
        with self.assertRaises(ValidationError):
            pengajuan.terima(self.kasir)

    # ---------- batalkan ----------

    def test_pelanggan_bisa_membatalkan_yang_masih_menunggu(self):
        pengajuan = self._pengajuan()
        pengajuan.batalkan()
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DIBATALKAN)

    def test_tidak_bisa_membatalkan_yang_sudah_diterima(self):
        pengajuan = self._pengajuan()
        pengajuan.terima(self.kasir)
        with self.assertRaises(ValidationError):
            pengajuan.batalkan()

    # ---------- aturan boleh/tidak boleh mengajukan ----------

    def test_kendaraan_dengan_pengajuan_menunggu_tidak_bisa_diajukan_lagi(self):
        self._pengajuan()
        alasan = PengajuanServis.alasan_kendaraan_tidak_bisa(self.kendaraan)
        self.assertIsNotNone(alasan)
        self.assertIn("menunggu", alasan.lower())

    def test_kendaraan_yang_sedang_diservis_tidak_bisa_diajukan(self):
        TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.kendaraan,
            keluhan="sedang dikerjakan",
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
        )
        alasan = PengajuanServis.alasan_kendaraan_tidak_bisa(self.kendaraan)
        self.assertIsNotNone(alasan)
        self.assertIn("belum selesai", alasan.lower())

    def test_kendaraan_bebas_boleh_diajukan(self):
        self.assertIsNone(
            PengajuanServis.alasan_kendaraan_tidak_bisa(self.kendaraan)
        )

    def test_pengajuan_yang_sudah_ditolak_tidak_menghalangi_pengajuan_baru(self):
        pertama = self._pengajuan()
        pertama.tolak(self.kasir, "Bengkel penuh.")
        self.assertIsNone(
            PengajuanServis.alasan_kendaraan_tidak_bisa(self.kendaraan)
        )

    def test_kendaraan_spesifik_polimorfis(self):
        """kendaraan_spesifik harus mengembalikan Motor, bukan Kendaraan induk."""
        pengajuan = self._pengajuan()
        self.assertEqual(pengajuan.kendaraan_spesifik.get_tipe(), "Motor")
