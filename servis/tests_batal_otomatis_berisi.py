"""FR-31 C: batal otomatis tidak boleh menghapus tagihan pekerjaan yang sudah dikerjakan.

Satu-satunya jalan transaksi yang SUDAH berisi layanan atau sparepart
kembali "menunggu kedatangan" adalah home service yang dialihkan ke bengkel
(lanjutkan_di_bengkel), yang memang boleh dilakukan saat status Dikerjakan.

Dulu: mekanik sudah memasang 3 busi di rumah pelanggan, lalu mengalihkan
pekerjaannya ke bengkel. Pelanggan tidak membawa kendaraannya, penyapu
membatalkan transaksinya. Tagihan Rp 75.000 jadi berstatus Dibatalkan, kasir
tidak bisa menagih (pembayaran hanya untuk status Selesai), dan stok busi
sudah berkurang tanpa ada yang membayar.

Sekarang transaksi yang sudah berisi pekerjaan tidak pernah dibatalkan
sendiri. Batasnya tetap dihitung dan kasir diberi tahu bahwa transaksi itu
perlu ditindaklanjuti, bukan menunggu hangus.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from mekanik.models import JenisServis
from servis.models import TransaksiServis as T
from sparepart.models import Sparepart


class BatalOtomatisTransaksiBerisi(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(username="k", password="x", role=User.ROLE_KASIR)
        mu = User.objects.create_user(username="m", password="x", role=User.ROLE_MEKANIK)
        self.mek = Mekanik.objects.create(user=mu, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda",
            model_kendaraan="Beat", tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)
        self.busi = Sparepart.objects.create(
            kode="S1", nama="Busi", kategori="Mesin", harga=25000, stok=10, stok_minimum=1)

    def home_service_dikerjakan(self):
        t = T.buka(keterangan="x", oleh=self.user, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="Mogok", mekanik=self.mek, tipe_layanan=T.TIPE_HOME_SERVICE,
                   lokasi_servis="Jl. Mawar 10", status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
                   kendaraan_hadir=False)
        t.terima_home_service()
        t.input_diagnosis("Busi mati", "Ganti busi")
        t.konfirmasi(True)
        return t

    def lewatkan_batas(self, t):
        T.objects.filter(pk=t.pk).update(
            tanggal=t.tanggal - timedelta(days=10),
            tanggal_rencana_datang=timezone.localdate() - timedelta(days=5),
        )
        t.refresh_from_db()

    def test_sparepart_sudah_dipasang_tidak_dibatalkan(self):
        """Inti laporannya."""
        t = self.home_service_dikerjakan()
        t.tambah_sparepart(self.busi, 3)
        t.lanjutkan_di_bengkel(timezone.localdate())
        self.lewatkan_batas(t)

        self.assertEqual(T.sapu_kedatangan_lewat(), 0)
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_DIKERJAKAN)
        self.assertTrue(t.kedatangan_lewat_batas, "batasnya tetap terlewati, hanya tidak dibatalkan")
        with self.assertRaises(ValidationError):
            t.batalkan_karena_tidak_datang()

    def test_layanan_sudah_dicatat_tidak_dibatalkan(self):
        t = self.home_service_dikerjakan()
        t.tambah_layanan(JenisServis.objects.create(
            nama_servis="Tune Up", harga=150000, estimasi_waktu=60))
        t.lanjutkan_di_bengkel(timezone.localdate())
        self.lewatkan_batas(t)

        self.assertEqual(T.sapu_kedatangan_lewat(), 0)

    def test_belum_ada_pekerjaan_tetap_dibatalkan(self):
        """Perilaku FR-31 C yang lama tidak boleh ikut berubah."""
        t = self.home_service_dikerjakan()
        t.lanjutkan_di_bengkel(timezone.localdate())
        self.lewatkan_batas(t)

        self.assertEqual(T.sapu_kedatangan_lewat(), 1)
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_DIBATALKAN)

    def test_kasir_diberi_tahu_untuk_menindaklanjuti(self):
        t = self.home_service_dikerjakan()
        t.tambah_sparepart(self.busi, 3)
        t.lanjutkan_di_bengkel(timezone.localdate())
        self.lewatkan_batas(t)

        self.client.force_login(self.kasir)
        respons = self.client.get("/kasir/transaksi/")
        self.assertContains(respons, "hubungi pelanggan")
        self.assertNotContains(respons, "Hangus bila belum tiba")
