"""FR-31: pengajuan yang diterima menceritakan nasib transaksinya.

Status PengajuanServis hanya mencatat keputusan kasir: Menunggu, Diterima,
Ditolak, atau Dibatalkan pelanggan. Sesudah diterima, cerita sebenarnya
pindah ke transaksi — bisa dikerjakan, selesai, ditolak pelanggan, atau
batal karena kendaraannya tidak pernah dibawa.

Dulu halaman kasir hanya membaca status pengajuan, jadi pengajuan yang
transaksinya sudah batal sendiri tetap tertulis "Diterima" dengan lencana hijau.
Halaman pelanggan sudah benar, tapi dengan menulis ulang logikanya sendiri
di template.

Sekarang satu properti, PengajuanServis.status_akhir, yang menjawab, dan
kedua halaman membacanya. Datanya sengaja TIDAK diubah: status "Diterima"
tetap benar sebagai catatan keputusan kasir, dan menyalin status transaksi
ke pengajuan berarti menyimpan satu fakta di dua tempat yang suatu saat
pasti tidak sinkron.
"""
from datetime import timedelta

from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis


class DasarStatusAkhir(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi", password="demo12345", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(
            username="kasir9", password="demo12345", role=User.ROLE_KASIR)
        mek_user = User.objects.create_user(
            username="mek9", password="demo12345", role=User.ROLE_MEKANIK)
        self.mekanik = Mekanik.objects.create(
            user=mek_user, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1234 ZZ",
            merk="Honda", model_kendaraan="Beat", tahun=2020,
            jenis_motor="Matic", kapasitas_mesin=110)

    def ajukan(self):
        return PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Mesin kasar")

    def biarkan_lewat_batas(self, pengajuan):
        """Terima, lalu biarkan lewat batas sampai penyapu membatalkannya."""
        transaksi = pengajuan.terima(self.kasir)
        mundur = transaksi.tanggal - timedelta(
            days=TransaksiServis.BATAS_HARI_KEDATANGAN + 1)
        TransaksiServis.objects.filter(pk=transaksi.pk).update(tanggal=mundur)
        TransaksiServis.sapu_kedatangan_lewat()
        pengajuan.refresh_from_db()
        return pengajuan


class StatusAkhirMengikutiTransaksi(DasarStatusAkhir):
    def test_menunggu_kasir(self):
        akhir = self.ajukan().status_akhir
        self.assertEqual(akhir.nada, "menunggu")
        self.assertIn("Menunggu", akhir.label)

    def test_ditolak_kasir(self):
        pengajuan = self.ajukan()
        pengajuan.tolak(self.kasir, "Bengkel penuh")
        self.assertEqual(pengajuan.status_akhir.nada, "gagal")
        self.assertEqual(pengajuan.status_akhir.label, "Ditolak")

    def test_dibatalkan_pelanggan(self):
        pengajuan = self.ajukan()
        pengajuan.batalkan()
        self.assertEqual(pengajuan.status_akhir.nada, "netral")

    def test_diterima_menunggu_kendaraan(self):
        pengajuan = self.ajukan()
        pengajuan.terima(self.kasir)
        akhir = pengajuan.status_akhir
        self.assertEqual(akhir.nada, "proses")
        self.assertIn("menunggu kendaraan", akhir.label.lower())

    def test_batal_otomatis_tidak_lagi_tertulis_diterima(self):
        """Inti perbaikannya."""
        pengajuan = self.biarkan_lewat_batas(self.ajukan())

        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DITERIMA,
                         "keputusan kasir tetap tersimpan apa adanya")
        akhir = pengajuan.status_akhir
        self.assertEqual(akhir.nada, "gagal")
        self.assertIn("tidak dibawa", akhir.label)

    def test_dikerjakan_lalu_selesai(self):
        pengajuan = self.ajukan()
        transaksi = pengajuan.terima(self.kasir)
        transaksi.tandai_kendaraan_tiba()
        transaksi.ambil_oleh(self.mekanik)
        transaksi.save()
        self.assertEqual(pengajuan.status_akhir.nada, "proses")

        transaksi.input_diagnosis("Kampas aus", "Ganti kampas")
        transaksi.konfirmasi(True)
        transaksi.selesaikan()
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status_akhir.nada, "selesai")
        self.assertEqual(pengajuan.status_akhir.label, "Selesai")

    def test_pelanggan_menolak_diagnosis_bukan_batal_otomatis(self):
        """Batal karena ditolak pelanggan berbeda dari batal karena tidak datang."""
        pengajuan = self.ajukan()
        transaksi = pengajuan.terima(self.kasir)
        transaksi.tandai_kendaraan_tiba()
        transaksi.ambil_oleh(self.mekanik)
        transaksi.save()
        transaksi.input_diagnosis("Mesin turun", "Overhaul")
        transaksi.konfirmasi(False)
        pengajuan.refresh_from_db()

        akhir = pengajuan.status_akhir
        self.assertEqual(akhir.nada, "gagal")
        self.assertNotIn("tidak dibawa", akhir.label)


class KeduaHalamanMembacaStatusAkhir(DasarStatusAkhir):
    def test_kasir_melihat_batal_otomatis_bukan_diterima(self):
        self.biarkan_lewat_batas(self.ajukan())

        self.client.force_login(self.kasir)
        respons = self.client.get("/kasir/pengajuan/?status=")
        self.assertContains(respons, "Dibatalkan: kendaraan tidak dibawa")
        # Hanya lencananya yang diperiksa: kata "Diterima" tetap wajar muncul
        # sebagai pilihan di dropdown filter status.
        self.assertNotContains(respons, '">Diterima</span>')

    def test_pelanggan_melihat_batal_otomatis(self):
        self.biarkan_lewat_batas(self.ajukan())

        self.client.force_login(self.user)
        respons = self.client.get("/pelanggan/pengajuan-saya/")
        self.assertContains(respons, "Dibatalkan: kendaraan tidak dibawa")
