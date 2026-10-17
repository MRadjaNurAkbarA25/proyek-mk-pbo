"""Uji halaman untuk penanda kedatangan dan ubah tanggal (FR-31 lanjutan)."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis

SANDI = "rahasia12345"


class HalamanKedatanganTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="pel", password=SANDI, role=User.ROLE_PELANGGAN
        )
        self.pelanggan = Pelanggan.objects.create(user=user)
        user_lain = User.objects.create_user(
            username="pel2", password=SANDI, role=User.ROLE_PELANGGAN
        )
        self.pelanggan_lain = Pelanggan.objects.create(user=user_lain)
        self.kasir = User.objects.create_user(
            username="kas", password=SANDI, role=User.ROLE_KASIR
        )
        self.kendaraan = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 88 UJ", merk="Honda",
            model_kendaraan="Beat", tahun=2021, jenis_motor="Matic",
            kapasitas_mesin=110,
        )
        self.pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.kendaraan,
            keluhan="Rem belakang bunyi berdecit",
        )

    # ---------- kasir menandai kedatangan ----------

    def test_kasir_menandai_kendaraan_tiba(self):
        t = self.pengajuan.terima(self.kasir)
        self.client.login(username="kas", password=SANDI)
        respons = self.client.post(reverse("kasir_tandai_tiba", args=[t.pk]))
        self.assertRedirects(respons, reverse("kasir_transaksi_detail", args=[t.pk]))
        t.refresh_from_db()
        self.assertTrue(t.kendaraan_hadir)

    def test_tandai_tiba_wajib_post(self):
        t = self.pengajuan.terima(self.kasir)
        self.client.login(username="kas", password=SANDI)
        self.assertEqual(
            self.client.get(reverse("kasir_tandai_tiba", args=[t.pk])).status_code, 405
        )
        t.refresh_from_db()
        self.assertFalse(t.kendaraan_hadir)

    def test_pelanggan_tidak_bisa_menandai_tiba(self):
        t = self.pengajuan.terima(self.kasir)
        self.client.login(username="pel", password=SANDI)
        self.client.post(reverse("kasir_tandai_tiba", args=[t.pk]))
        t.refresh_from_db()
        self.assertFalse(t.kendaraan_hadir)

    def test_tombol_tandai_tiba_tampil_di_detail(self):
        t = self.pengajuan.terima(self.kasir)
        self.client.login(username="kas", password=SANDI)
        isi = self.client.get(reverse("kasir_transaksi_detail", args=[t.pk])).content.decode()
        self.assertIn("Tandai Kendaraan Tiba", isi)
        self.assertIn("Kendaraan belum tiba di bengkel", isi)

    def test_tombol_hilang_setelah_ditandai(self):
        t = self.pengajuan.terima(self.kasir)
        t.tandai_kendaraan_tiba()
        self.client.login(username="kas", password=SANDI)
        isi = self.client.get(reverse("kasir_transaksi_detail", args=[t.pk])).content.decode()
        self.assertNotIn("Tandai Kendaraan Tiba", isi)

    def test_keterangan_kedatangan_tampil_di_daftar_transaksi(self):
        besok = timezone.localdate() + timedelta(days=1)
        self.pengajuan.tanggal_rencana_datang = besok
        self.pengajuan.save(update_fields=["tanggal_rencana_datang"])
        self.pengajuan.terima(self.kasir)

        self.client.login(username="kas", password=SANDI)
        isi = self.client.get(reverse("kasir_transaksi_daftar")).content.decode()
        self.assertIn("Tiba di bengkel:", isi)

    def test_daftar_transaksi_menyebut_tanggal_belum_diisi(self):
        self.pengajuan.terima(self.kasir)
        self.client.login(username="kas", password=SANDI)
        isi = self.client.get(reverse("kasir_transaksi_daftar")).content.decode()
        self.assertIn("tanggal belum diisi", isi)

    # ---------- pelanggan mengubah tanggal ----------

    def _url_tanggal(self):
        return reverse("ubah_tanggal_datang", args=[self.pengajuan.pk])

    def test_ubah_tanggal_sebelum_diterima_mengubah_pengajuan(self):
        besok = timezone.localdate() + timedelta(days=1)
        self.client.login(username="pel", password=SANDI)
        respons = self.client.post(
            self._url_tanggal(), {"tanggal_rencana_datang": besok.isoformat()}
        )
        self.assertRedirects(respons, reverse("pengajuan_saya"))
        self.pengajuan.refresh_from_db()
        self.assertEqual(self.pengajuan.tanggal_rencana_datang, besok)

    def test_ubah_tanggal_sesudah_diterima_mengubah_transaksi(self):
        besok = timezone.localdate() + timedelta(days=1)
        lusa = timezone.localdate() + timedelta(days=2)
        self.pengajuan.tanggal_rencana_datang = besok
        self.pengajuan.save(update_fields=["tanggal_rencana_datang"])
        t = self.pengajuan.terima(self.kasir)

        self.client.login(username="pel", password=SANDI)
        self.client.post(self._url_tanggal(), {"tanggal_rencana_datang": lusa.isoformat()})

        t.refresh_from_db()
        self.pengajuan.refresh_from_db()
        self.assertEqual(t.tanggal_rencana_datang, lusa)
        self.assertEqual(
            self.pengajuan.tanggal_rencana_datang, besok,
            "catatan pengajuan tidak boleh ikut berubah",
        )

    def test_tidak_bisa_ubah_tanggal_setelah_kendaraan_tiba(self):
        t = self.pengajuan.terima(self.kasir)
        t.tandai_kendaraan_tiba()
        lusa = timezone.localdate() + timedelta(days=2)

        self.client.login(username="pel", password=SANDI)
        respons = self.client.post(
            self._url_tanggal(), {"tanggal_rencana_datang": lusa.isoformat()}
        )
        self.assertRedirects(respons, reverse("pengajuan_saya"))
        t.refresh_from_db()
        self.assertIsNone(t.tanggal_rencana_datang)

    def test_tanggal_masa_lalu_ditolak_form(self):
        kemarin = timezone.localdate() - timedelta(days=1)
        self.client.login(username="pel", password=SANDI)
        self.client.post(
            self._url_tanggal(), {"tanggal_rencana_datang": kemarin.isoformat()}
        )
        self.pengajuan.refresh_from_db()
        self.assertIsNone(self.pengajuan.tanggal_rencana_datang)

    def test_pelanggan_lain_tidak_bisa_membuka(self):
        self.client.login(username="pel2", password=SANDI)
        self.assertEqual(self.client.get(self._url_tanggal()).status_code, 404)

    def test_kasir_tidak_bisa_membuka_halaman_pelanggan(self):
        self.client.login(username="kas", password=SANDI)
        self.assertEqual(self.client.get(self._url_tanggal()).status_code, 302)

    def test_tombol_ubah_tanggal_tampil_selama_masih_berguna(self):
        self.client.login(username="pel", password=SANDI)
        isi = self.client.get(reverse("pengajuan_saya")).content.decode()
        self.assertIn("Ubah Tanggal", isi)

    def test_tombol_ubah_tanggal_hilang_setelah_kendaraan_tiba(self):
        t = self.pengajuan.terima(self.kasir)
        t.tandai_kendaraan_tiba()
        self.client.login(username="pel", password=SANDI)
        isi = self.client.get(reverse("pengajuan_saya")).content.decode()
        self.assertNotIn("Ubah Tanggal", isi)
        self.assertIn("Kendaraan sudah tiba", isi)
