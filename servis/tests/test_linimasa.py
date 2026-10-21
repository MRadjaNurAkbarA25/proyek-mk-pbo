"""FR-32: linimasa perkembangan servis terisi sendiri.

Nilai fitur ini ada pada kata "sendiri". Kalau linimasanya perlu diisi
manual, suatu saat pasti ada alur yang lupa mengisinya dan pelanggan
melihat jejak yang bolong. Jadi yang diuji di sini bukan "barisnya bisa
dibuat", melainkan "barisnya muncul tanpa ada yang menyuruh".
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PembaruanServis, PengajuanServis, TransaksiServis


class DasarLinimasa(TestCase):
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

    def tahap(self, transaksi):
        return [p.tahap for p in transaksi.pembaruan.all()]


class LinimasaTerisiSendiri(DasarLinimasa):
    def test_alur_lengkap_mencatat_setiap_tahap_berurutan(self):
        """Tidak satu pun baris di bawah ini ditulis manual oleh tes."""
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Rem bunyi")
        transaksi = pengajuan.terima(self.kasir)
        transaksi.tandai_kendaraan_tiba()
        transaksi.ambil_oleh(self.mekanik)
        transaksi.save()
        transaksi.input_diagnosis("Kampas aus", "Ganti kampas rem")
        transaksi.konfirmasi(True)
        transaksi.selesaikan()

        self.assertEqual(self.tahap(transaksi), [
            PembaruanServis.TAHAP_PERMINTAAN,
            PembaruanServis.TAHAP_KEDATANGAN,
            PembaruanServis.TAHAP_PEMERIKSAAN,
            PembaruanServis.TAHAP_PERSETUJUAN,
            PembaruanServis.TAHAP_PERBAIKAN,
            PembaruanServis.TAHAP_SELESAI,
        ])

    def test_urutannya_maju_bukan_mundur(self):
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Rem bunyi")
        transaksi = pengajuan.terima(self.kasir)
        transaksi.tandai_kendaraan_tiba()

        waktu = [p.waktu for p in transaksi.pembaruan.all()]
        self.assertEqual(waktu, sorted(waktu), "linimasa harus dibaca dari yang paling awal")

    def test_pelanggan_yang_menolak_diagnosis_tercatat_sebagai_batal(self):
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Rem bunyi")
        transaksi = pengajuan.terima(self.kasir)
        transaksi.tandai_kendaraan_tiba()
        transaksi.ambil_oleh(self.mekanik)
        transaksi.save()
        transaksi.input_diagnosis("Mesin turun", "Overhaul, biaya besar")
        transaksi.konfirmasi(False)

        terakhir = transaksi.pembaruan.last()
        self.assertEqual(terakhir.tahap, PembaruanServis.TAHAP_BATAL)
        self.assertIn("menolak", terakhir.keterangan.lower())

    def test_batal_otomatis_ikut_tercatat(self):
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Rem bunyi")
        transaksi = pengajuan.terima(self.kasir)
        mundur = transaksi.tanggal - timedelta(
            days=TransaksiServis.BATAS_HARI_KEDATANGAN + 1)
        TransaksiServis.objects.filter(pk=transaksi.pk).update(tanggal=mundur)
        transaksi.refresh_from_db()

        TransaksiServis.sapu_kedatangan_lewat()

        terakhir = transaksi.pembaruan.last()
        self.assertEqual(terakhir.tahap, PembaruanServis.TAHAP_BATAL)
        self.assertIn("batas waktu", terakhir.keterangan.lower())

    def test_pencatat_ikut_disimpan(self):
        """Siapa yang melakukan ikut tercatat, supaya jejaknya bisa ditelusuri."""
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Rem bunyi")
        transaksi = pengajuan.terima(self.kasir)

        self.assertEqual(transaksi.pembaruan.first().oleh, self.kasir)


class LinimasaDiHalamanPelanggan(DasarLinimasa):
    def siapkan(self):
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Rem bunyi")
        transaksi = pengajuan.terima(self.kasir)
        transaksi.tandai_kendaraan_tiba()
        return transaksi

    def test_pelanggan_melihat_linimasanya(self):
        transaksi = self.siapkan()
        self.client.force_login(self.user)
        respons = self.client.get(f"/pelanggan/riwayat/{transaksi.pk}/")

        self.assertEqual(respons.status_code, 200)
        self.assertContains(respons, "Perkembangan Servis")
        self.assertContains(respons, "Kendaraan tiba di bengkel")

    def test_pelanggan_lain_tidak_bisa_mengintip(self):
        transaksi = self.siapkan()
        orang_lain = User.objects.create_user(
            username="orang2", password="demo12345", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=orang_lain)

        self.client.force_login(orang_lain)
        respons = self.client.get(f"/pelanggan/riwayat/{transaksi.pk}/")
        self.assertNotEqual(respons.status_code, 200)


class TransaksiTanpaLinimasaTetapTampil(DasarLinimasa):
    """Transaksi yang dibuat langsung lewat ORM, mis. oleh seed_demo.

    Tanpa penanganan ini, kartu "Perkembangan Servis" tampil kosong dan
    terlihat seperti fitur rusak. Ini kejadian nyata di database yang baru
    dibuat: migrasi pengisian jalan saat tabelnya masih kosong, lalu
    seed_demo membuat transaksi sesudahnya.
    """

    def test_kartu_tidak_pernah_kosong(self):
        transaksi = TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor,
            keluhan="Dibuat langsung tanpa lewat method",
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
            status=TransaksiServis.STATUS_MENUNGGU,
        )
        self.assertEqual(transaksi.pembaruan.count(), 0)

        self.client.force_login(self.user)
        respons = self.client.get(f"/pelanggan/riwayat/{transaksi.pk}/")
        self.assertContains(respons, "Transaksi servis dibuat")
        self.assertNotContains(respons, "Belum ada pembaruan")


class KosakataTahapDipakaiBersama(TestCase):
    def test_stepper_mekanik_memakai_label_yang_sama(self):
        """Dua tampilan tidak boleh menyebut tahap yang sama dengan nama berbeda."""
        from mekanik.progres import LANGKAH

        label_stepper = {nama for nama, _, _ in LANGKAH}
        label_linimasa = set(dict(PembaruanServis.TAHAP_CHOICES).values())
        self.assertTrue(
            label_stepper <= label_linimasa,
            f"label stepper di luar kosakata linimasa: {label_stepper - label_linimasa}",
        )
