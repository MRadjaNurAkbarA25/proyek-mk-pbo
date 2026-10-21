"""Uji penanda kehadiran kendaraan dan rencana tanggal datang (FR-31 lanjutan).

Inti yang dijaga: transaksi hasil pengajuan pelanggan TIDAK boleh bisa diambil
mekanik sebelum kendaraannya benar-benar tiba di bengkel.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis

SANDI = "rahasia12345"


class KehadiranKendaraanTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="pel", password=SANDI, role=User.ROLE_PELANGGAN
        )
        self.pelanggan = Pelanggan.objects.create(user=user)
        self.kasir = User.objects.create_user(
            username="kas", password=SANDI, role=User.ROLE_KASIR
        )
        user_mek = User.objects.create_user(
            username="mek", password=SANDI, role=User.ROLE_MEKANIK
        )
        self.mekanik = Mekanik.objects.create(user=user_mek)
        self.kendaraan = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 77 UJ", merk="Honda",
            model_kendaraan="Vario", tahun=2022, jenis_motor="Matic",
            kapasitas_mesin=125,
        )

    def _pengajuan(self, tanggal=None):
        return PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.kendaraan,
            keluhan="Rem belakang bunyi", tanggal_rencana_datang=tanggal,
        )

    # ---------- nilai bawaan ----------

    def test_transaksi_buatan_kasir_dianggap_sudah_hadir(self):
        """Walk-in: kendaraannya memang sudah di depan mata, jadi True."""
        t = TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.kendaraan, keluhan="walk-in",
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
        )
        self.assertTrue(t.kendaraan_hadir)
        self.assertFalse(t.menunggu_kedatangan)

    def test_transaksi_dari_pengajuan_lahir_belum_hadir(self):
        t = self._pengajuan().terima(self.kasir)
        self.assertFalse(t.kendaraan_hadir)
        self.assertTrue(t.menunggu_kedatangan)

    def test_tanggal_disalin_dari_pengajuan_ke_transaksi(self):
        besok = timezone.localdate() + timedelta(days=1)
        t = self._pengajuan(tanggal=besok).terima(self.kasir)
        self.assertEqual(t.tanggal_rencana_datang, besok)

    # ---------- antrian mekanik ----------

    def test_belum_hadir_tidak_muncul_di_antrian(self):
        self._pengajuan().terima(self.kasir)
        self.client.login(username="mek", password=SANDI)
        antrian = self.client.get(reverse("mekanik_antrian")).context["antrian_bengkel"]
        self.assertEqual(list(antrian), [])

    def test_muncul_di_antrian_setelah_ditandai_tiba(self):
        t = self._pengajuan().terima(self.kasir)
        t.tandai_kendaraan_tiba()

        self.client.login(username="mek", password=SANDI)
        antrian = self.client.get(reverse("mekanik_antrian")).context["antrian_bengkel"]
        self.assertEqual([x.pk for x in antrian], [t.pk])

    def test_mekanik_tidak_bisa_mengambil_yang_belum_tiba(self):
        """Dijaga di model, bukan cuma disembunyikan dari daftar."""
        t = self._pengajuan().terima(self.kasir)
        with self.assertRaises(ValidationError):
            t.ambil_oleh(self.mekanik)
        t.refresh_from_db()
        self.assertIsNone(t.mekanik)

    def test_mekanik_bisa_mengambil_setelah_tiba(self):
        t = self._pengajuan().terima(self.kasir)
        t.tandai_kendaraan_tiba()
        t.ambil_oleh(self.mekanik)
        t.refresh_from_db()
        self.assertEqual(t.mekanik, self.mekanik)

    # ---------- menandai kedatangan ----------

    def test_tidak_bisa_menandai_dua_kali(self):
        t = self._pengajuan().terima(self.kasir)
        t.tandai_kendaraan_tiba()
        with self.assertRaises(ValidationError):
            t.tandai_kendaraan_tiba()

    def test_tidak_bisa_menandai_transaksi_yang_sudah_dibatalkan(self):
        t = self._pengajuan().terima(self.kasir)
        t.status = TransaksiServis.STATUS_DIBATALKAN
        t.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            t.tandai_kendaraan_tiba()

    def test_menunggu_kedatangan_padam_saat_transaksi_tidak_aktif(self):
        t = self._pengajuan().terima(self.kasir)
        self.assertTrue(t.menunggu_kedatangan)
        t.status = TransaksiServis.STATUS_DIBATALKAN
        t.save(update_fields=["status"])
        self.assertFalse(t.menunggu_kedatangan)

    # ---------- ubah tanggal ----------

    def test_pengajuan_belum_ditinjau_bisa_ubah_tanggalnya_sendiri(self):
        p = self._pengajuan()
        besok = timezone.localdate() + timedelta(days=1)
        p.ubah_rencana_datang(besok)
        p.refresh_from_db()
        self.assertEqual(p.tanggal_rencana_datang, besok)

    def test_pengajuan_yang_sudah_diterima_tidak_bisa_diubah_lagi(self):
        """Catatan keputusan harus tetap utuh; yang berubah transaksinya."""
        p = self._pengajuan()
        p.terima(self.kasir)
        with self.assertRaises(ValidationError):
            p.ubah_rencana_datang(timezone.localdate() + timedelta(days=1))

    def test_transaksi_bisa_ubah_tanggal_selama_belum_tiba(self):
        t = self._pengajuan().terima(self.kasir)
        lusa = timezone.localdate() + timedelta(days=2)
        t.ubah_rencana_datang(lusa)
        t.refresh_from_db()
        self.assertEqual(t.tanggal_rencana_datang, lusa)

    def test_transaksi_tidak_bisa_ubah_tanggal_setelah_tiba(self):
        t = self._pengajuan().terima(self.kasir)
        t.tandai_kendaraan_tiba()
        with self.assertRaises(ValidationError):
            t.ubah_rencana_datang(timezone.localdate() + timedelta(days=2))

    def test_tanggal_masa_lalu_ditolak(self):
        t = self._pengajuan().terima(self.kasir)
        with self.assertRaises(ValidationError):
            t.ubah_rencana_datang(timezone.localdate() - timedelta(days=1))

    def test_tanggal_boleh_dikosongkan(self):
        besok = timezone.localdate() + timedelta(days=1)
        t = self._pengajuan(tanggal=besok).terima(self.kasir)
        t.ubah_rencana_datang(None)
        t.refresh_from_db()
        self.assertIsNone(t.tanggal_rencana_datang)

    # ---------- pengajuan asli tidak ikut berubah ----------

    def test_tanggal_pengajuan_tetap_utuh_saat_transaksi_diubah(self):
        besok = timezone.localdate() + timedelta(days=1)
        minggu_depan = timezone.localdate() + timedelta(days=7)
        p = self._pengajuan(tanggal=besok)
        t = p.terima(self.kasir)

        t.ubah_rencana_datang(minggu_depan)

        p.refresh_from_db()
        t.refresh_from_db()
        self.assertEqual(p.tanggal_rencana_datang, besok, "catatan pengajuan berubah")
        self.assertEqual(t.tanggal_rencana_datang, minggu_depan)
