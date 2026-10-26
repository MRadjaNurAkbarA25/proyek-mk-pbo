"""Kejadian pembayaran tercatat di linimasa servis (FR-32).

Pelanggan yang buktinya ditolak harus tahu tanpa membuka halaman bayar:
alasannya muncul di Perkembangan Servis dan angka kabar baru menyala.
"""
import io
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from pembayaran.models import BuktiPembayaran, Pembayaran
from pembayaran.tests.test_alur_bayar import DasarAlurBayar, berkas_png
from servis.models import PembaruanServis, TransaksiServis

PEMBAYARAN = PembaruanServis.TAHAP_PEMBAYARAN


class LinimasaPembayaran(DasarAlurBayar):
    def kirim(self, t):
        return BuktiPembayaran.ajukan(
            t, self.pelanggan, jenis=BuktiPembayaran.JENIS_BANK,
            nama_penyedia="BRI", nomor_referensi="REF-1", berkas=berkas_png())

    def terakhir(self, t):
        return t.pembaruan.order_by("-pk").first()

    def test_bukti_dikirim_tercatat_tanpa_menyalakan_kabar_pelanggan(self):
        t = self.transaksi()
        t.tandai_dibaca_pelanggan()
        self.kirim(t)
        baris = self.terakhir(t)
        self.assertEqual(baris.tahap, PEMBAYARAN)
        self.assertIn("dikirim", baris.keterangan)
        self.assertEqual(baris.oleh, self.pelanggan.user)
        self.assertEqual(TransaksiServis.berkabar_baru_untuk(self.pelanggan).count(), 0)

    def test_nama_penyedia_tidak_ditulis_dobel(self):
        t = self.transaksi()
        BuktiPembayaran.ajukan(
            t, self.pelanggan, jenis=BuktiPembayaran.JENIS_E_MONEY,
            nama_penyedia="QRIS", nomor_referensi="Q-1", berkas=berkas_png())
        self.assertEqual(self.terakhir(t).keterangan.count("QRIS"), 1)

    def test_disetujui_tercatat_dan_menyalakan_kabar(self):
        t = self.transaksi()
        bukti = self.kirim(t)
        t.tandai_dibaca_pelanggan()
        bukti.setujui(self.kasir)
        baris = self.terakhir(t)
        self.assertEqual(baris.tahap, PEMBAYARAN)
        self.assertIn("diterima", baris.keterangan)
        self.assertEqual(baris.oleh, self.kasir)
        self.assertEqual(list(TransaksiServis.berkabar_baru_untuk(self.pelanggan)), [t])

    def test_ditolak_alasannya_tercatat_dan_menyalakan_kabar(self):
        t = self.transaksi()
        bukti = self.kirim(t)
        t.tandai_dibaca_pelanggan()
        bukti.tolak(self.kasir, "Nominal tidak sesuai tagihan")
        baris = self.terakhir(t)
        self.assertEqual(baris.tahap, PEMBAYARAN)
        self.assertIn("Nominal tidak sesuai tagihan", baris.keterangan)
        self.assertEqual(TransaksiServis.berkabar_baru_untuk(self.pelanggan).count(), 1)

    def test_alasan_panjang_dipotong_sesuai_batas_kolom(self):
        t = self.transaksi()
        self.kirim(t).tolak(self.kasir, "x" * 500)
        batas = PembaruanServis._meta.get_field("keterangan").max_length
        self.assertLessEqual(len(self.terakhir(t).keterangan), batas)

    def test_cash_tercatat_sekali_walau_dikirim_ulang(self):
        t = self.transaksi()
        Pembayaran.catat_cash(t, Decimal("200000"), oleh=self.kasir)
        Pembayaran.catat_cash(t, Decimal("200000"), oleh=self.kasir)  # klik ganda
        tunai = t.pembaruan.filter(tahap=PEMBAYARAN)
        self.assertEqual(tunai.count(), 1)
        self.assertIn("tunai", tunai.get().keterangan)


TMP_SEED = tempfile.mkdtemp(prefix="bukti_seed_")


@override_settings(BUKTI_BAYAR_ROOT=Path(TMP_SEED))
class SeedDemoPembayaran(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_SEED, ignore_errors=True)

    def seed(self, **kw):
        call_command("seed_demo", verbosity=0, stdout=io.StringIO(), izinkan_di_server=True, **kw)

    def test_ada_contoh_menunggu_ditolak_dan_lunas(self):
        self.seed()
        self.assertEqual(BuktiPembayaran.objects.filter(status=BuktiPembayaran.STATUS_MENUNGGU).count(), 1)
        self.assertEqual(BuktiPembayaran.objects.filter(status=BuktiPembayaran.STATUS_DITOLAK).count(), 1)
        self.assertEqual(Pembayaran.objects.count(), 1)

    def test_reset_berulang_tidak_gagal_karena_bukti(self):
        self.seed()
        self.seed(reset=True)
        self.seed(reset=True)
        self.assertEqual(BuktiPembayaran.objects.count(), 2)
        self.assertEqual(Pembayaran.objects.count(), 1)
