"""Pelanggan tidak bisa menghapus kendaraan yang punya riwayat servis.

Dulu TransaksiServis terhubung ke Kendaraan dengan on_delete=CASCADE, dan
halaman hapus kendaraan hanya menahan transaksi yang SUDAH DIBAYAR (lewat
PROTECT di Pembayaran). Akibatnya:

- servis yang selesai tapi belum dibayar ikut terhapus bersama kendaraannya,
  jadi pelanggan bisa menghapus tagihannya sendiri sebelum ke kasir;
- servis yang sedang dikerjakan mekanik lenyap di tengah jalan;
- sparepart yang sudah terpakai hilang dari catatan, padahal stoknya sudah
  berkurang.

Sekarang dua lapis: Kendaraan.alasan_tidak_bisa_dihapus() untuk pesan yang
jelas, dan on_delete=PROTECT di database untuk jalur lain (misalnya /admin/).
"""
from django.db.models import ProtectedError
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Kendaraan, Motor
from mekanik.models import JenisServis
from servis.models import TransaksiServis as T
from sparepart.models import Sparepart


class DasarKendaraan(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(username="k", password="x", role=User.ROLE_KASIR)
        mu = User.objects.create_user(username="m", password="x", role=User.ROLE_MEKANIK)
        self.mek = Mekanik.objects.create(user=mu, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda",
            model_kendaraan="Beat", tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)
        self.client.force_login(self.user)


class HapusKendaraan(DasarKendaraan):
    def hapus(self):
        return self.client.post(f"/pelanggan/kendaraan/hapus/{self.motor.pk}/", follow=True)

    def servis_selesai_belum_dibayar(self):
        sp = Sparepart.objects.create(kode="S1", nama="Busi", kategori="Mesin",
                                      harga=25000, stok=10, stok_minimum=1)
        js = JenisServis.objects.create(nama_servis="Tune Up", harga=150000, estimasi_waktu=60)
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        t.ambil_oleh(self.mek)
        t.save()
        t.input_diagnosis("a", "b")
        t.konfirmasi(True)
        t.tambah_layanan(js)
        t.tambah_sparepart(sp, 2)
        t.selesaikan()
        return t

    def test_tagihan_belum_dibayar_tidak_bisa_dihapus_pelanggan(self):
        """Inti laporannya."""
        t = self.servis_selesai_belum_dibayar()
        respons = self.hapus()

        self.assertTrue(T.objects.filter(pk=t.pk).exists(), "tagihan tidak boleh hilang")
        self.assertTrue(Kendaraan.objects.filter(pk=self.motor.pk).exists())
        self.assertContains(respons, "riwayat servis")

    def test_servis_yang_sedang_berjalan_tidak_bisa_dihapus(self):
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        self.hapus()
        self.assertTrue(T.objects.filter(pk=t.pk).exists())

    def test_servis_yang_dibatalkan_pun_tetap_riwayat(self):
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        T.objects.filter(pk=t.pk).update(status=T.STATUS_DIBATALKAN)
        self.hapus()
        self.assertTrue(T.objects.filter(pk=t.pk).exists())

    def test_kendaraan_tanpa_riwayat_tetap_bisa_dihapus(self):
        """Salah input nomor polisi harus tetap bisa diperbaiki pelanggan."""
        respons = self.hapus()
        self.assertFalse(Kendaraan.objects.filter(pk=self.motor.pk).exists())
        self.assertContains(respons, "berhasil dihapus")

    def test_database_ikut_menjaga_jalur_lain(self):
        """Lewat /admin/ atau shell pun, transaksi tidak ikut terhapus."""
        self.servis_selesai_belum_dibayar()
        with self.assertRaises(ProtectedError):
            Kendaraan.objects.filter(pk=self.motor.pk).delete()

    def test_tombol_hapus_hanya_untuk_kendaraan_tanpa_riwayat(self):
        url = f"/pelanggan/kendaraan/hapus/{self.motor.pk}/"
        self.assertContains(self.client.get("/pelanggan/kendaraan/"), url)

        T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
               keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        self.assertNotContains(self.client.get("/pelanggan/kendaraan/"), url)


class LabelSedangDiprosesDiHomeService(DasarKendaraan):
    """Form Home Service memberi keterangan seperti form Ajukan Servis."""

    def test_kendaraan_sibuk_diberi_keterangan(self):
        url = "/pelanggan/home-service/pesan/"
        self.assertNotContains(self.client.get(url), "sedang diproses")
        T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
               keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        self.assertContains(self.client.get(url), "(KT 1 A) — sedang diproses")
