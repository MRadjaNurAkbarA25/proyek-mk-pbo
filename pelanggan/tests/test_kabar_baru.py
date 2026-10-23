"""Angka di menu pelanggan: ada kabar baru, atau ada yang harus dijawab.

Dua angka, dua makna:

- Persetujuan Diagnosis: jumlah diagnosis yang menunggu jawaban pelanggan.
  Mekanik tidak boleh mulai bekerja sebelum dijawab, jadi ini yang paling
  perlu terlihat dari halaman mana pun.
- Riwayat Service: jumlah transaksi yang linimasanya punya baris baru
  sejak terakhir kali pelanggan membuka detailnya. Baris yang ditulis
  pelanggan sendiri (memesan home service, menyetujui diagnosis) tidak
  dihitung sebagai kabar baru — dia sudah tahu, dia yang melakukannya.

Membuka Detail Riwayat Service menandai transaksi itu sudah dibaca.
"""
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis

URL_RIWAYAT = "/pelanggan/riwayat/"


class DasarKabar(TestCase):
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

    def transaksi_kasir(self):
        return TransaksiServis.buka(
            keterangan="Didaftarkan kasir.", oleh=self.kasir,
            pelanggan=self.pelanggan, kendaraan=self.motor,
            keluhan="Rem bunyi", tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL)

    def baca(self, t):
        self.client.force_login(self.user)
        return self.client.get(f"/pelanggan/riwayat/{t.pk}/")

    def jumlah_kabar(self):
        return TransaksiServis.berkabar_baru_untuk(self.pelanggan).count()


class AturanKabarBaru(DasarKabar):
    def test_transaksi_baru_dari_kasir_adalah_kabar(self):
        self.transaksi_kasir()
        self.assertEqual(self.jumlah_kabar(), 1)

    def test_membuka_detail_menandai_sudah_dibaca(self):
        t = self.transaksi_kasir()
        self.assertEqual(self.baca(t).status_code, 200)
        self.assertEqual(self.jumlah_kabar(), 0)

    def test_baris_baru_sesudah_dibaca_menyalakan_lagi(self):
        t = self.transaksi_kasir()
        self.baca(t)
        t.ambil_oleh(self.mekanik)
        t.save()
        self.assertEqual(self.jumlah_kabar(), 1)

    def test_kabar_tulisan_mekanik_dihitung(self):
        t = self.transaksi_kasir()
        t.ambil_oleh(self.mekanik)
        t.save()
        self.baca(t)
        t.tulis_pembaruan(self.mekanik, "Sedang dibongkar.")
        self.assertEqual(self.jumlah_kabar(), 1)

    def test_kabar_di_tick_jam_yang_sama_dengan_baca_tetap_dihitung(self):
        """Jam berbutir kasar: waktu baca dan baris baru bisa sama persis.

        Dulu dibandingkan dengan `waktu > dibaca`, jadi kabar ini hilang dan
        tesnya flaky. Jam dibekukan supaya kasus itu terjadi setiap kali.
        """
        from unittest import mock
        from django.utils import timezone
        with mock.patch("django.utils.timezone.now", return_value=timezone.now()):
            t = self.transaksi_kasir()
            t.ambil_oleh(self.mekanik)
            t.save()
            self.baca(t)
            self.assertEqual(self.jumlah_kabar(), 0)
            t.tulis_pembaruan(self.mekanik, "Sedang dibongkar.")
            self.assertEqual(self.jumlah_kabar(), 1)

    def test_tindakan_pelanggan_sendiri_tidak_dihitung(self):
        """Menyetujui diagnosis lalu melihat angka menyala itu membingungkan."""
        t = self.transaksi_kasir()
        t.ambil_oleh(self.mekanik)
        t.save()
        t.input_diagnosis("Kampas aus", "Ganti kampas")
        self.baca(t)
        t.konfirmasi(True)  # ditulis atas nama pelanggan
        self.assertEqual(self.jumlah_kabar(), 0)

    def test_dihitung_per_transaksi_bukan_per_baris(self):
        t = self.transaksi_kasir()
        t.ambil_oleh(self.mekanik)
        t.save()
        t.tulis_pembaruan(self.mekanik, "Satu.")
        t.tulis_pembaruan(self.mekanik, "Dua.")
        self.assertEqual(self.jumlah_kabar(), 1)

    def test_pengajuan_diterima_dan_batal_otomatis_menyala(self):
        """Dua kabar FR-31 yang dulu tidak sampai ke pelanggan sama sekali."""
        from datetime import timedelta
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Oli bocor")
        t = pengajuan.terima(self.kasir)
        self.assertEqual(self.jumlah_kabar(), 1, "pengajuan diterima = kabar")

        self.baca(t)
        mundur = t.tanggal - timedelta(days=TransaksiServis.BATAS_HARI_KEDATANGAN + 1)
        TransaksiServis.objects.filter(pk=t.pk).update(tanggal=mundur)
        TransaksiServis.sapu_kedatangan_lewat()
        self.assertEqual(self.jumlah_kabar(), 1, "batal otomatis = kabar")

    def test_milik_pelanggan_lain_tidak_ikut(self):
        lain = User.objects.create_user(
            username="sari", password="demo12345", role=User.ROLE_PELANGGAN)
        p_lain = Pelanggan.objects.create(user=lain)
        motor_lain = Motor.objects.create(
            pelanggan=p_lain, no_polisi="KT 9 X", merk="Yamaha",
            model_kendaraan="Mio", tahun=2019, jenis_motor="Matic",
            kapasitas_mesin=125)
        TransaksiServis.buka(
            keterangan="Didaftarkan kasir.", oleh=self.kasir,
            pelanggan=p_lain, kendaraan=motor_lain, keluhan="x",
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL)
        self.assertEqual(self.jumlah_kabar(), 0)


class AngkaDiMenu(DasarKabar):
    def test_angka_riwayat_tampil_dan_hilang_setelah_dibaca(self):
        t = self.transaksi_kasir()
        self.client.force_login(self.user)
        respons = self.client.get(URL_RIWAYAT)
        self.assertContains(respons, 'data-kabar="riwayat">1<')
        self.assertContains(respons, "kabar-baru", msg_prefix="baris transaksinya ditandai")

        self.baca(t)
        respons = self.client.get(URL_RIWAYAT)
        self.assertNotContains(respons, 'data-kabar="riwayat"')

    def test_angka_persetujuan_diagnosis(self):
        t = self.transaksi_kasir()
        t.ambil_oleh(self.mekanik)
        t.save()
        t.input_diagnosis("Kampas aus", "Ganti kampas")

        self.client.force_login(self.user)
        respons = self.client.get("/pelanggan/dashboard/")
        self.assertContains(respons, 'data-kabar="persetujuan">1<')

        t.konfirmasi(True)
        respons = self.client.get("/pelanggan/dashboard/")
        self.assertNotContains(respons, 'data-kabar="persetujuan"')

    def test_role_lain_tidak_terkena_query_tambahan(self):
        """Context processor hanya bekerja untuk pelanggan."""
        self.transaksi_kasir()
        self.client.force_login(self.kasir)
        respons = self.client.get("/kasir/transaksi/")
        self.assertNotIn("jumlah_kabar_riwayat", respons.context)
