"""FR-31 bagian C: transaksi batal sendiri kalau kendaraannya tidak kunjung datang.

Yang diuji di sini bukan "halamannya hidup", tapi perhitungan batasnya.
Tiap tes di bawah mewakili satu cacat logika yang sempat ada di rancangan
dan sengaja dikunci supaya tidak kembali.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis


class DasarKedatangan(TestCase):
    def setUp(self):
        self.hari_ini = timezone.localdate()
        self.user = User.objects.create_user(
            username="budi", password="demo12345", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(
            username="kasir9", password="demo12345", role=User.ROLE_KASIR)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1234 ZZ",
            merk="Honda", model_kendaraan="Beat", tahun=2020,
            jenis_motor="Matic", kapasitas_mesin=110)

    def ajukan(self, rencana=None):
        return PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor,
            keluhan="Mesin kasar", tanggal_rencana_datang=rencana)

    def mundurkan(self, transaksi, hari):
        """Geser tanggal pembuatan transaksi ke masa lalu.

        `tanggal` memakai auto_now_add sehingga tidak bisa diisi saat
        create; satu-satunya cara menguji lewatnya waktu adalah menulis
        langsung ke basis data lewat update().
        """
        baru = transaksi.tanggal - timedelta(days=hari)
        TransaksiServis.objects.filter(pk=transaksi.pk).update(tanggal=baru)
        transaksi.refresh_from_db()
        return transaksi


class BatasDihitungDariYangLebihBelakangan(DasarKedatangan):
    """Cacat 1: transaksi tidak boleh lahir dalam keadaan sudah kedaluwarsa."""

    def test_kasir_terlambat_menyetujui_tidak_bikin_transaksi_langsung_batal(self):
        # Pelanggan minta datang 5 hari lalu, kasir baru menyetujui HARI INI.
        pengajuan = self.ajukan(rencana=self.hari_ini - timedelta(days=5))
        transaksi = pengajuan.terima(self.kasir)

        # Kalau batas dihitung dari rencana datang saja, hasilnya sudah lewat
        # dan transaksi ini batal beberapa detik setelah disetujui.
        self.assertEqual(
            transaksi.batas_kedatangan(),
            self.hari_ini + timedelta(days=TransaksiServis.BATAS_HARI_KEDATANGAN),
            "Batas harus dihitung dari tanggal persetujuan, bukan rencana yang sudah lewat",
        )
        self.assertFalse(transaksi.kedatangan_lewat_batas)
        self.assertEqual(TransaksiServis.sapu_kedatangan_lewat(), 0)

    def test_rencana_di_masa_depan_yang_dipakai(self):
        # Rencana 10 hari lagi: pelanggan dapat 3 hari SESUDAH tanggal itu.
        rencana = self.hari_ini + timedelta(days=10)
        transaksi = self.ajukan(rencana=rencana).terima(self.kasir)
        self.assertEqual(
            transaksi.batas_kedatangan(),
            rencana + timedelta(days=TransaksiServis.BATAS_HARI_KEDATANGAN),
        )

    def test_tanpa_rencana_dihitung_dari_tanggal_persetujuan(self):
        transaksi = self.ajukan(rencana=None).terima(self.kasir)
        self.assertEqual(
            transaksi.batas_kedatangan(),
            self.hari_ini + timedelta(days=TransaksiServis.BATAS_HARI_KEDATANGAN),
        )


class PenyapuMembatalkan(DasarKedatangan):
    def test_lewat_batas_dibatalkan_dan_dihitung(self):
        transaksi = self.ajukan().terima(self.kasir)
        self.mundurkan(transaksi, TransaksiServis.BATAS_HARI_KEDATANGAN + 1)

        self.assertTrue(transaksi.kedatangan_lewat_batas)
        self.assertEqual(TransaksiServis.sapu_kedatangan_lewat(), 1)

        transaksi.refresh_from_db()
        self.assertEqual(transaksi.status, TransaksiServis.STATUS_DIBATALKAN)

    def test_tepat_di_hari_batas_belum_dibatalkan(self):
        """Batatasnya inklusif: hari terakhir masih boleh dipakai."""
        transaksi = self.ajukan().terima(self.kasir)
        self.mundurkan(transaksi, TransaksiServis.BATAS_HARI_KEDATANGAN)

        self.assertEqual(transaksi.batas_kedatangan(), self.hari_ini)
        self.assertFalse(transaksi.kedatangan_lewat_batas)
        self.assertEqual(TransaksiServis.sapu_kedatangan_lewat(), 0)

    def test_kendaraan_sudah_tiba_tidak_pernah_dibatalkan(self):
        transaksi = self.ajukan().terima(self.kasir)
        transaksi.tandai_kendaraan_tiba()
        self.mundurkan(transaksi, 99)

        self.assertIsNone(transaksi.batas_kedatangan())
        self.assertEqual(TransaksiServis.sapu_kedatangan_lewat(), 0)
        transaksi.refresh_from_db()
        self.assertNotEqual(transaksi.status, TransaksiServis.STATUS_DIBATALKAN)

    def test_batalkan_manual_ditolak_kalau_belum_lewat(self):
        transaksi = self.ajukan().terima(self.kasir)
        with self.assertRaises(ValidationError):
            transaksi.batalkan_karena_tidak_datang()


class HomeServiceTidakIkutTersapu(DasarKedatangan):
    """Home service kendaraannya memang tidak pernah datang ke bengkel."""

    def buat_home_service(self):
        mekanik_user = User.objects.create_user(
            username="mek9", password="demo12345", role=User.ROLE_MEKANIK)
        mekanik = Mekanik.objects.create(user=mekanik_user)
        return TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, mekanik=mekanik,
            keluhan="Tidak mau hidup",
            tipe_layanan=TransaksiServis.TIPE_HOME_SERVICE,
            lokasi_servis="Jl. Mawar 10",
            status=TransaksiServis.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
            kendaraan_hadir=False,
        )

    def test_home_service_lama_tidak_dibatalkan(self):
        transaksi = self.buat_home_service()
        self.mundurkan(transaksi, 99)

        self.assertFalse(transaksi.menunggu_kedatangan)
        self.assertIsNone(transaksi.batas_kedatangan())
        self.assertEqual(TransaksiServis.sapu_kedatangan_lewat(), 0)

    def test_dialihkan_ke_bengkel_mulai_menunggu_kedatangan(self):
        """Cacat lama: kendaraan masih di rumah pelanggan tapi tercatat sudah di bengkel."""
        transaksi = self.buat_home_service()
        transaksi.terima_home_service()
        rencana = self.hari_ini + timedelta(days=2)
        transaksi.lanjutkan_di_bengkel(rencana)

        self.assertEqual(transaksi.tipe_layanan, TransaksiServis.TIPE_DI_BENGKEL)
        self.assertFalse(transaksi.kendaraan_hadir)
        self.assertTrue(transaksi.menunggu_kedatangan)
        self.assertEqual(transaksi.tanggal_rencana_datang, rencana)
        self.assertEqual(
            transaksi.batas_kedatangan(),
            rencana + timedelta(days=TransaksiServis.BATAS_HARI_KEDATANGAN),
        )

    def test_dialihkan_tanpa_tanggal_ditolak(self):
        transaksi = self.buat_home_service()
        transaksi.terima_home_service()
        with self.assertRaises(ValidationError):
            transaksi.lanjutkan_di_bengkel(None)

    def test_dialihkan_dengan_tanggal_masa_lalu_ditolak(self):
        transaksi = self.buat_home_service()
        transaksi.terima_home_service()
        with self.assertRaises(ValidationError):
            transaksi.lanjutkan_di_bengkel(self.hari_ini - timedelta(days=1))


class PenyapuJalanDariHalamanPelanggan(DasarKedatangan):
    """Cacat 5: tanpa ini, pelanggan melihat transaksi yang seharusnya sudah batal."""

    def test_membuka_pengajuan_saya_ikut_menyapu(self):
        transaksi = self.ajukan().terima(self.kasir)
        self.mundurkan(transaksi, TransaksiServis.BATAS_HARI_KEDATANGAN + 1)

        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/pelanggan/pengajuan-saya/").status_code, 200)

        transaksi.refresh_from_db()
        self.assertEqual(transaksi.status, TransaksiServis.STATUS_DIBATALKAN)

    def test_membuka_riwayat_ikut_menyapu(self):
        transaksi = self.ajukan().terima(self.kasir)
        self.mundurkan(transaksi, TransaksiServis.BATAS_HARI_KEDATANGAN + 1)

        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/pelanggan/riwayat/").status_code, 200)

        transaksi.refresh_from_db()
        self.assertEqual(transaksi.status, TransaksiServis.STATUS_DIBATALKAN)

    def test_pengajuan_saya_menampilkan_status_transaksi_bukan_status_pengajuan(self):
        """Cacat 2: pengajuan selamanya tertulis Diterima walau transaksinya batal."""
        pengajuan = self.ajukan()
        transaksi = pengajuan.terima(self.kasir)
        self.mundurkan(transaksi, TransaksiServis.BATAS_HARI_KEDATANGAN + 1)

        self.client.force_login(self.user)
        isi = self.client.get("/pelanggan/pengajuan-saya/").content.decode()

        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DITERIMA)
        self.assertIn("Batal otomatis", isi)
        self.assertIn("Dibatalkan", isi)
