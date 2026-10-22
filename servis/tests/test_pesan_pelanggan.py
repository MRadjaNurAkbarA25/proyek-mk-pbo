"""QoL A4: pelanggan menulis pertanyaan ke linimasa, mekanik diberi tanda.

Kebalikan dari kabar mekanik (FR-32). Pelanggan yang servisnya sedang
dipegang mekanik bisa menulis satu kalimat ke linimasa yang sama; mekanik
pemegang melihat angka "pesan baru" di menunya sampai dia membuka detailnya.

Bukan chat: tidak ada status dibaca untuk pelanggan, tidak ada notifikasi.
Mekanik menjawab lewat kabar biasa. Hal mendesak lewat tombol WhatsApp.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PembaruanServis, TransaksiServis as T


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        lain = User.objects.create_user(username="sari", password="x", role=User.ROLE_PELANGGAN)
        self.p_lain = Pelanggan.objects.create(user=lain)
        self.kasir = User.objects.create_user(username="kasir", password="x", role=User.ROLE_KASIR)
        mu = User.objects.create_user(username="mek", password="x", role=User.ROLE_MEKANIK)
        self.mek = Mekanik.objects.create(user=mu, status=Mekanik.STATUS_TERSEDIA)
        mu2 = User.objects.create_user(username="mek2", password="x", role=User.ROLE_MEKANIK)
        self.mek2 = Mekanik.objects.create(user=mu2, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda", model_kendaraan="Beat",
            tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)

    def buka_transaksi(self, diambil=True):
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="Rem bunyi", tipe_layanan=T.TIPE_DI_BENGKEL)
        if diambil:
            t.ambil_oleh(self.mek)
            t.save()
        return t


class AturanMenulisPesan(Dasar):
    def test_pemilik_bisa_bertanya_saat_dipegang_mekanik(self):
        t = self.buka_transaksi()
        baris = t.tulis_pesan_pelanggan(self.p, "  Kira-kira selesai jam berapa?  ")
        self.assertEqual(baris.keterangan, "Kira-kira selesai jam berapa?")
        self.assertEqual(baris.oleh, self.user)
        self.assertEqual(baris.tahap, PembaruanServis.TAHAP_PEMERIKSAAN)
        self.assertTrue(baris.dari_pelanggan)

    def test_menulis_tidak_memindahkan_status(self):
        t = self.buka_transaksi()
        t.tulis_pesan_pelanggan(self.p, "Halo")
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_MENUNGGU)

    def test_pelanggan_lain_ditolak(self):
        t = self.buka_transaksi()
        with self.assertRaises(ValidationError):
            t.tulis_pesan_pelanggan(self.p_lain, "Halo")

    def test_belum_ada_mekanik_ditolak(self):
        t = self.buka_transaksi(diambil=False)
        self.assertFalse(t.bisa_ditanya_pelanggan)
        with self.assertRaises(ValidationError):
            t.tulis_pesan_pelanggan(self.p, "Halo")

    def test_sudah_selesai_ditolak(self):
        t = self.buka_transaksi()
        T.objects.filter(pk=t.pk).update(status=T.STATUS_SELESAI)
        t.refresh_from_db()
        with self.assertRaises(ValidationError):
            t.tulis_pesan_pelanggan(self.p, "Halo")

    def test_kosong_dan_terlalu_panjang_ditolak(self):
        t = self.buka_transaksi()
        with self.assertRaises(ValidationError):
            t.tulis_pesan_pelanggan(self.p, "   ")
        with self.assertRaises(ValidationError):
            t.tulis_pesan_pelanggan(self.p, "x" * 201)

    def test_kabar_mekanik_bukan_dari_pelanggan(self):
        t = self.buka_transaksi()
        self.assertFalse(t.tulis_pembaruan(self.mek, "Sedang dicek").dari_pelanggan)


class TandaPesanBaruMekanik(Dasar):
    def test_pesan_pelanggan_menyalakan_tanda_untuk_pemegang_saja(self):
        t = self.buka_transaksi()
        self.assertEqual(T.berpesan_baru_untuk_mekanik(self.mek).count(), 0)
        t.tulis_pesan_pelanggan(self.p, "Halo")
        self.assertEqual(list(T.berpesan_baru_untuk_mekanik(self.mek)), [t])
        self.assertEqual(T.berpesan_baru_untuk_mekanik(self.mek2).count(), 0)

    def test_kabar_mekanik_dan_catatan_sistem_tidak_menyalakan_tanda(self):
        t = self.buka_transaksi()
        t.tulis_pembaruan(self.mek, "Sedang dicek")
        t.catat(PembaruanServis.TAHAP_PEMERIKSAAN, "catatan sistem")
        self.assertEqual(T.berpesan_baru_untuk_mekanik(self.mek).count(), 0)

    def test_dibuka_mekanik_mematikan_tanda_sampai_ada_pesan_baru(self):
        t = self.buka_transaksi()
        t.tulis_pesan_pelanggan(self.p, "Halo")
        t.tandai_dibaca_mekanik()
        self.assertEqual(T.berpesan_baru_untuk_mekanik(self.mek).count(), 0)
        t.tulis_pesan_pelanggan(self.p, "Masih di sana?")
        self.assertEqual(T.berpesan_baru_untuk_mekanik(self.mek).count(), 1)

    def test_tindakan_pelanggan_bukan_pesan(self):
        """Menyetujui diagnosis dicatat atas nama pelanggan, tapi itu bukan pertanyaan."""
        t = self.buka_transaksi()
        t.input_diagnosis("Kampas aus", "Ganti kampas")
        t.konfirmasi(True)
        self.assertTrue(t.pembaruan.filter(oleh=self.user).exists())
        self.assertEqual(T.berpesan_baru_untuk_mekanik(self.mek).count(), 0)
        self.assertFalse(any(b.dari_pelanggan for b in t.pembaruan.all()))

    def test_pesan_pelanggan_tidak_menyalakan_tanda_pelanggan_sendiri(self):
        t = self.buka_transaksi()
        t.tandai_dibaca_pelanggan()
        t.tulis_pesan_pelanggan(self.p, "Halo")
        self.assertEqual(T.berkabar_baru_untuk(self.p).count(), 0)


class LewatHalaman(Dasar):
    def url_kirim(self, t):
        return f"/pelanggan/riwayat/{t.pk}/pesan/"

    def test_pelanggan_mengirim_lalu_mekanik_melihat_angka_dan_pesannya(self):
        t = self.buka_transaksi()
        self.client.force_login(self.user)
        r = self.client.get(f"/pelanggan/riwayat/{t.pk}/")
        self.assertContains(r, 'action="%s"' % self.url_kirim(t))
        r = self.client.post(self.url_kirim(t), {"keterangan": "Ada biaya tambahan?"}, follow=True)
        self.assertContains(r, "Pesan terkirim")
        self.assertContains(r, "Ada biaya tambahan?")

        self.client.force_login(self.mek.user)
        beranda = self.client.get("/mekanik/dashboard/")
        self.assertEqual(beranda.context["jumlah_pesan_pelanggan"], 1)
        detail = self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertContains(detail, "Ada biaya tambahan?")
        self.assertContains(detail, "dari-pelanggan")
        self.assertEqual(self.client.get("/mekanik/dashboard/").context["jumlah_pesan_pelanggan"], 0)

    def test_form_tidak_tampil_bila_belum_ada_mekanik(self):
        t = self.buka_transaksi(diambil=False)
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(f"/pelanggan/riwayat/{t.pk}/"), self.url_kirim(t))

    def test_transaksi_orang_lain_404(self):
        t = self.buka_transaksi()
        self.client.force_login(self.p_lain.user)
        self.assertEqual(self.client.post(self.url_kirim(t), {"keterangan": "pesan nyasar"}).status_code, 404)
        self.assertFalse(t.pembaruan.filter(keterangan="pesan nyasar").exists())

    def test_get_tidak_diizinkan(self):
        t = self.buka_transaksi()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url_kirim(t)).status_code, 405)

    def test_tidak_ada_query_tambahan_di_halaman_lain(self):
        """Angka mekanik hanya dihitung untuk mekanik yang login."""
        from mekanik.context_processors import pesan_pelanggan
        from django.test import RequestFactory
        req = RequestFactory().get("/")
        req.user = self.user
        self.assertEqual(pesan_pelanggan(req), {})
