"""FR-32: mekanik menulis kabar perkembangan sendiri.

Linimasa yang terisi otomatis menjawab "sudah sampai tahap mana", tapi
tidak menjawab hal-hal yang hanya diketahui mekanik: sedang menunggu
sparepart, sedang uji jalan, ternyata ada kerusakan lain. Sekarang
mekanik yang memegang transaksi bisa menulis satu kalimat, dan pelanggan
membacanya di linimasa yang sama.

Aturannya dijaga di TransaksiServis.tulis_pembaruan(), bukan di view:
- hanya mekanik yang memegang transaksi itu,
- hanya selama pekerjaannya berjalan,
- tahapnya mengikuti status saat itu, jadi tidak ada tahap baru dan
  tidak perlu migrasi,
- menulis kabar tidak pernah memindahkan status.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from mekanik.models import JenisServis
from servis.models import PembaruanServis, TransaksiServis


class DasarPembaruanMekanik(TestCase):
    def setUp(self):
        # selesaikan() butuh minimal satu layanan.
        self.layanan = JenisServis.objects.create(
            nama_servis="Servis Rem", harga=50000, estimasi_waktu=30)
        self.user = User.objects.create_user(
            username="budi", password="demo12345", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(
            username="kasir9", password="demo12345", role=User.ROLE_KASIR)
        mek_user = User.objects.create_user(
            username="mek9", password="demo12345", role=User.ROLE_MEKANIK)
        self.mekanik = Mekanik.objects.create(
            user=mek_user, status=Mekanik.STATUS_TERSEDIA)
        lain_user = User.objects.create_user(
            username="mek10", password="demo12345", role=User.ROLE_MEKANIK)
        self.mekanik_lain = Mekanik.objects.create(
            user=lain_user, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1234 ZZ",
            merk="Honda", model_kendaraan="Beat", tahun=2020,
            jenis_motor="Matic", kapasitas_mesin=110)

    def transaksi_diambil(self):
        t = TransaksiServis.buka(
            keterangan="Didaftarkan kasir.", oleh=self.kasir,
            pelanggan=self.pelanggan, kendaraan=self.motor,
            keluhan="Rem bunyi", tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL)
        t.ambil_oleh(self.mekanik)
        t.save()
        return t

    def transaksi_dikerjakan(self):
        t = self.transaksi_diambil()
        t.input_diagnosis("Kampas aus", "Ganti kampas")
        t.konfirmasi(True)
        return t


class AturanMenulisPembaruan(DasarPembaruanMekanik):
    def test_pemegang_bisa_menulis_saat_dikerjakan(self):
        t = self.transaksi_dikerjakan()
        baris = t.tulis_pembaruan(self.mekanik, "Menunggu kampas rem datang dari gudang.")

        self.assertEqual(baris.tahap, PembaruanServis.TAHAP_PERBAIKAN)
        self.assertEqual(baris.oleh, self.mekanik.user)
        self.assertEqual(t.pembaruan.last(), baris)

    def test_tahap_mengikuti_status_saat_itu(self):
        t = self.transaksi_diambil()
        self.assertEqual(
            t.tulis_pembaruan(self.mekanik, "Sedang dibongkar.").tahap,
            PembaruanServis.TAHAP_PEMERIKSAAN)

        t.input_diagnosis("Kampas aus", "Ganti kampas")
        self.assertEqual(
            t.tulis_pembaruan(self.mekanik, "Menunggu jawaban Anda.").tahap,
            PembaruanServis.TAHAP_PERSETUJUAN)

    def test_menulis_tidak_memindahkan_status(self):
        t = self.transaksi_dikerjakan()
        t.tulis_pembaruan(self.mekanik, "Uji jalan.")
        t.refresh_from_db()
        self.assertEqual(t.status, TransaksiServis.STATUS_DIKERJAKAN)

    def test_mekanik_lain_ditolak(self):
        t = self.transaksi_dikerjakan()
        with self.assertRaises(ValidationError):
            t.tulis_pembaruan(self.mekanik_lain, "Bukan pekerjaan saya.")
        self.assertFalse(t.pembaruan.filter(oleh=self.mekanik_lain.user).exists())

    def test_ditolak_setelah_selesai(self):
        t = self.transaksi_dikerjakan()
        t.tambah_layanan(self.layanan)
        t.selesaikan()
        with self.assertRaises(ValidationError):
            t.tulis_pembaruan(self.mekanik, "Terlambat.")

    def test_ditolak_sebelum_home_service_diterima(self):
        """Sebelum menekan Terima, mekanik belum memegang pekerjaannya."""
        t = TransaksiServis.buka(
            keterangan="Panggilan dikirim.", oleh=self.user,
            pelanggan=self.pelanggan, kendaraan=self.motor,
            keluhan="Mogok", mekanik=self.mekanik,
            tipe_layanan=TransaksiServis.TIPE_HOME_SERVICE,
            lokasi_servis="Jl. Mawar 10",
            status=TransaksiServis.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
            kendaraan_hadir=False)
        with self.assertRaises(ValidationError):
            t.tulis_pembaruan(self.mekanik, "Saya berangkat.")

    def test_kosong_ditolak(self):
        t = self.transaksi_dikerjakan()
        with self.assertRaises(ValidationError):
            t.tulis_pembaruan(self.mekanik, "   ")

    def test_tahap_kabar_memakai_kosakata_linimasa(self):
        """TAHAP_KABAR_MEKANIK ditulis sebagai teks karena PembaruanServis
        didefinisikan sesudah TransaksiServis. Tes ini menjaga keduanya cocok."""
        sah = {kode for kode, _ in PembaruanServis.TAHAP_CHOICES}
        self.assertLessEqual(set(TransaksiServis.TAHAP_KABAR_MEKANIK.values()), sah)

    def test_terlalu_panjang_ditolak_bukan_dipotong_diam_diam(self):
        t = self.transaksi_dikerjakan()
        with self.assertRaises(ValidationError):
            t.tulis_pembaruan(self.mekanik, "x" * 201)


class PembaruanLewatHalaman(DasarPembaruanMekanik):
    def url(self, t):
        return f"/mekanik/servis/{t.pk}/pembaruan/"

    def test_pemegang_menulis_lalu_pelanggan_membacanya(self):
        t = self.transaksi_dikerjakan()
        self.client.force_login(self.mekanik.user)
        respons = self.client.post(self.url(t), {"keterangan": "Sedang uji jalan keliling blok."})
        self.assertEqual(respons.status_code, 302)

        self.client.force_login(self.user)
        respons = self.client.get(f"/pelanggan/riwayat/{t.pk}/")
        self.assertContains(respons, "Sedang uji jalan keliling blok.")

    def test_mekanik_lain_tidak_bisa_menulis_lewat_url(self):
        t = self.transaksi_dikerjakan()
        jumlah = t.pembaruan.count()
        self.client.force_login(self.mekanik_lain.user)
        respons = self.client.post(self.url(t), {"keterangan": "Iseng."})
        self.assertEqual(respons.status_code, 404)
        self.assertEqual(t.pembaruan.count(), jumlah)

    def test_get_tidak_diizinkan(self):
        t = self.transaksi_dikerjakan()
        self.client.force_login(self.mekanik.user)
        self.assertEqual(self.client.get(self.url(t)).status_code, 405)

    def test_form_tampil_hanya_saat_bisa_menulis(self):
        t = self.transaksi_dikerjakan()
        self.client.force_login(self.mekanik.user)
        respons = self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertContains(respons, self.url(t))

        t.tambah_layanan(self.layanan)
        t.selesaikan()
        respons = self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertNotContains(respons, self.url(t))
        # Linimasanya tetap terlihat walau form-nya hilang.
        self.assertContains(respons, "linimasa")
