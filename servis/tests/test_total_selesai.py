"""Masukan dosen: ada servis SELESAI dengan total Rp 0,00.

Aturannya di model: selesaikan() butuh minimal satu layanan. Tampilan total
lewat TransaksiServis.total_tampil: belum ada angka sebelum dikerjakan,
"sementara" selama dikerjakan, final setelah selesai, kosong kalau batal.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from mekanik.models import JenisServis
from servis.models import TotalTampil, TransaksiServis as T


class DasarTotal(TestCase):
    def setUp(self):
        u = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=u)
        m = User.objects.create_user(username="mek", password="x", role=User.ROLE_MEKANIK)
        self.mekanik = Mekanik.objects.create(user=m, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1 A", merk="Honda",
            model_kendaraan="Beat", tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)
        self.oli = JenisServis.objects.create(nama_servis="Ganti Oli", harga=50000, estimasi_waktu=30)

    def transaksi(self, status, **data):
        data.setdefault("mekanik", self.mekanik)
        return T.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor,
            tipe_layanan=T.TIPE_DI_BENGKEL, status=status, **data)


class SelesaikanButuhLayanan(DasarTotal):
    def test_tanpa_layanan_ditolak_dan_status_tetap(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN)
        self.assertFalse(t.bisa_diselesaikan)
        with self.assertRaisesMessage(
                ValidationError, "Tambahkan minimal satu layanan sebelum menyelesaikan servis."):
            t.selesaikan()
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_DIKERJAKAN)

    def test_dengan_satu_layanan_berhasil(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN)
        t.tambah_layanan(self.oli)
        self.assertTrue(t.bisa_diselesaikan)
        t.selesaikan()
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_SELESAI)
        self.assertEqual(t.total_biaya, Decimal("50000"))

    def test_bukan_dikerjakan_tidak_bisa_diselesaikan(self):
        t = self.transaksi(T.STATUS_MENUNGGU)
        self.assertFalse(t.bisa_diselesaikan)


class TotalTampilPerStatus(DasarTotal):
    def test_sebelum_dikerjakan_belum_ada_angka(self):
        for status in (T.STATUS_MENUNGGU, T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
                       T.STATUS_MENUNGGU_KONFIRMASI):
            with self.subTest(status=status):
                self.assertEqual(self.transaksi(status).total_tampil,
                                 TotalTampil(None, "Dihitung setelah diagnosis"))

    def test_dikerjakan_sementara(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN)
        t.tambah_layanan(self.oli)
        self.assertEqual(t.total_tampil, TotalTampil(Decimal("50000"), "sementara"))

    def test_selesai_final(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN)
        t.tambah_layanan(self.oli)
        t.selesaikan()
        self.assertEqual(t.total_tampil, TotalTampil(Decimal("50000"), ""))

    def test_dibatalkan_tanpa_angka(self):
        t = self.transaksi(T.STATUS_DIBATALKAN, total_biaya=Decimal("75000"))
        self.assertEqual(t.total_tampil, TotalTampil(None, ""))


class TampilanHalaman(DasarTotal):
    def test_tombol_selesai_nonaktif_tanpa_layanan(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN)
        self.client.force_login(self.mekanik.user)
        html = self.client.get(f"/mekanik/servis/{t.pk}/").content.decode()
        self.assertIn("Selesaikan Servis</button>", html)
        tombol = html[html.index('action="/mekanik/servis/%d/selesai/"' % t.pk):]
        tombol = tombol[:tombol.index("</button>")]
        self.assertIn("disabled", tombol)
        self.assertIn("Tambahkan minimal satu layanan", html)

    def test_tombol_selesai_aktif_dengan_layanan(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN)
        t.tambah_layanan(self.oli)
        self.client.force_login(self.mekanik.user)
        html = self.client.get(f"/mekanik/servis/{t.pk}/").content.decode()
        tombol = html[html.index('action="/mekanik/servis/%d/selesai/"' % t.pk):]
        tombol = tombol[:tombol.index("</button>")]
        self.assertNotIn("disabled", tombol)

    def test_post_selesai_tanpa_layanan_ditolak(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN)
        self.client.force_login(self.mekanik.user)
        r = self.client.post(f"/mekanik/servis/{t.pk}/selesai/", follow=True)
        self.assertContains(r, "Tambahkan minimal satu layanan sebelum menyelesaikan servis.")
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_DIKERJAKAN)

    def test_riwayat_pelanggan(self):
        self.transaksi(T.STATUS_MENUNGGU)
        kerja = self.transaksi(T.STATUS_DIKERJAKAN)
        kerja.tambah_layanan(self.oli)
        self.client.force_login(self.pelanggan.user)
        r = self.client.get("/pelanggan/riwayat/")
        self.assertNotContains(r, "Rp 0,00")
        self.assertContains(r, "Dihitung setelah diagnosis")
        self.assertContains(r, "sementara")

    def test_daftar_kasir_dan_pengerjaan_mekanik(self):
        self.transaksi(T.STATUS_MENUNGGU, mekanik=None)
        self.transaksi(T.STATUS_DIBATALKAN, total_biaya=Decimal("75000"))
        kasir = User.objects.create_user(username="kasir", password="x", role=User.ROLE_KASIR)
        self.client.force_login(kasir)
        r = self.client.get("/kasir/transaksi/")
        self.assertNotContains(r, "Rp 0,00")
        self.assertNotContains(r, "Rp 75.000")
        self.assertContains(r, "Dihitung setelah diagnosis")

    def test_laporan_admin_tidak_berubah(self):
        self.transaksi(T.STATUS_MENUNGGU)
        admin = User.objects.create_user(username="admin", password="x", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        r = self.client.get("/adminpanel/laporan/transaksi/")
        self.assertContains(r, "Rp 0,00")
