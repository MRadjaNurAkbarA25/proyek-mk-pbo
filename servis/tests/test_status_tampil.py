"""Label status transaksi yang ditampilkan, dari sudut pandang staf dan pelanggan.

Masukan dosen: "Menunggu" tidak jelas menunggu siapa, dan "Selesai" padahal
belum dibayar. Nilai status di database tidak berubah; yang berubah hanya
TransaksiServis.status_tampil dan status_tampil_pelanggan (StatusAkhir).
"""
from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from pembayaran.models import BuktiPembayaran, Pembayaran
from servis.models import StatusAkhir, TransaksiServis as T


class DasarStatus(TestCase):
    def setUp(self):
        u = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=u)
        m = User.objects.create_user(username="mek", password="x", role=User.ROLE_MEKANIK)
        self.mekanik = Mekanik.objects.create(user=m)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1 A", merk="Honda",
            model_kendaraan="Beat", tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)

    def transaksi(self, status, **data):
        data.setdefault("tipe_layanan", T.TIPE_DI_BENGKEL)
        return T.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, status=status, **data)

    def bukti(self, t, status=BuktiPembayaran.STATUS_MENUNGGU):
        return BuktiPembayaran.objects.create(
            transaksi=t, jenis=BuktiPembayaran.JENIS_BANK, nama_penyedia="BRI",
            nomor_referensi=f"REF{t.pk}{status}", berkas="bukti_bayar/x.png", status=status)

    def assertStatus(self, t, staf, pelanggan, nada):
        t = T.objects.get(pk=t.pk)
        self.assertEqual(t.status_tampil, StatusAkhir(staf, nada))
        self.assertEqual(t.status_tampil_pelanggan, StatusAkhir(pelanggan, nada))


class PemetaanStatus(DasarStatus):
    """Satu tes per baris tabel pemetaan."""

    def test_menunggu_kendaraan_belum_tiba(self):
        t = self.transaksi(T.STATUS_MENUNGGU, kendaraan_hadir=False)
        self.assertStatus(t, "Menunggu kendaraan tiba", "Menunggu kendaraan Anda tiba", "menunggu")

    def test_menunggu_sudah_tiba_belum_ada_mekanik(self):
        t = self.transaksi(T.STATUS_MENUNGGU)
        self.assertStatus(t, "Menunggu mekanik", "Menunggu mekanik", "menunggu")

    def test_menunggu_sudah_ada_mekanik(self):
        t = self.transaksi(T.STATUS_MENUNGGU, mekanik=self.mekanik)
        self.assertStatus(t, "Diperiksa mekanik", "Sedang diperiksa mekanik", "proses")

    def test_menunggu_konfirmasi_mekanik(self):
        t = self.transaksi(T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
                           tipe_layanan=T.TIPE_HOME_SERVICE, mekanik=self.mekanik)
        self.assertStatus(t, "Menunggu mekanik menerima", "Menunggu mekanik menerima", "menunggu")

    def test_menunggu_konfirmasi_pelanggan(self):
        t = self.transaksi(T.STATUS_MENUNGGU_KONFIRMASI, mekanik=self.mekanik)
        self.assertStatus(t, "Menunggu persetujuan pelanggan", "Menunggu persetujuan Anda", "menunggu")

    def test_dikerjakan(self):
        t = self.transaksi(T.STATUS_DIKERJAKAN, mekanik=self.mekanik)
        self.assertStatus(t, "Sedang dikerjakan", "Sedang dikerjakan", "proses")

    def test_selesai_lunas(self):
        t = self.transaksi(T.STATUS_SELESAI, mekanik=self.mekanik)
        Pembayaran.objects.create(transaksi=t, total=0, metode=Pembayaran.METODE_CASH)
        self.assertStatus(t, "Selesai · Lunas", "Selesai · Lunas", "selesai")

    def test_selesai_bukti_menunggu(self):
        t = self.transaksi(T.STATUS_SELESAI, mekanik=self.mekanik)
        self.bukti(t)
        self.assertStatus(t, "Selesai · Menunggu verifikasi bayar",
                          "Selesai · Bukti sedang diperiksa", "menunggu")

    def test_selesai_belum_dibayar(self):
        t = self.transaksi(T.STATUS_SELESAI, mekanik=self.mekanik)
        self.assertStatus(t, "Selesai · Belum dibayar", "Selesai · Belum dibayar", "gagal")

    def test_dibatalkan(self):
        t = self.transaksi(T.STATUS_DIBATALKAN)
        self.assertStatus(t, "Dibatalkan", "Dibatalkan", "gagal")


class KasusDariTransisi(DasarStatus):
    """Kondisi yang muncul dari transisi sebenarnya tetapi tidak ada di tabel usulan."""

    def test_home_service_sudah_diterima_mekanik(self):
        # terima_home_service(): MENUNGGU_KONFIRMASI_MEKANIK -> MENUNGGU, mekanik
        # menuju atau sudah di lokasi pelanggan, bukan di bengkel.
        t = self.transaksi(T.STATUS_MENUNGGU, tipe_layanan=T.TIPE_HOME_SERVICE,
                           mekanik=self.mekanik)
        self.assertStatus(t, "Ditangani mekanik di lokasi",
                          "Ditangani mekanik di lokasi Anda", "proses")

    def test_lanjut_di_bengkel_saat_dikerjakan_menunggu_kendaraan(self):
        # lanjutkan_di_bengkel() boleh dari DIKERJAKAN dan menyetel kendaraan_hadir=False.
        t = self.transaksi(T.STATUS_DIKERJAKAN, tipe_layanan=T.TIPE_HOME_SERVICE,
                           mekanik=self.mekanik)
        t.lanjutkan_di_bengkel(timezone.localdate() + timedelta(days=1))
        self.assertEqual(T.objects.get(pk=t.pk).status, T.STATUS_DIKERJAKAN)
        self.assertStatus(t, "Menunggu kendaraan tiba", "Menunggu kendaraan Anda tiba", "menunggu")

    def test_lanjut_di_bengkel_sudah_ada_mekanik_tetap_menunggu_kendaraan(self):
        t = self.transaksi(T.STATUS_MENUNGGU, mekanik=self.mekanik, kendaraan_hadir=False)
        self.assertStatus(t, "Menunggu kendaraan tiba", "Menunggu kendaraan Anda tiba", "menunggu")

    def test_persetujuan_didahulukan_walau_kendaraan_belum_tiba(self):
        # Pelanggan tetap bisa (dan perlu) menjawab diagnosis sebelum kendaraannya dibawa.
        t = self.transaksi(T.STATUS_MENUNGGU_KONFIRMASI, mekanik=self.mekanik,
                           kendaraan_hadir=False)
        self.assertStatus(t, "Menunggu persetujuan pelanggan", "Menunggu persetujuan Anda", "menunggu")

    def test_bukti_ditolak_kembali_belum_dibayar(self):
        t = self.transaksi(T.STATUS_SELESAI, mekanik=self.mekanik)
        self.bukti(t, BuktiPembayaran.STATUS_DITOLAK)
        self.assertStatus(t, "Selesai · Belum dibayar", "Selesai · Belum dibayar", "gagal")

    def test_status_di_database_tidak_berubah(self):
        self.assertEqual(dict(T.STATUS_CHOICES)[T.STATUS_MENUNGGU], "Menunggu")
        t = self.transaksi(T.STATUS_SELESAI)
        self.assertEqual(t.get_status_display(), "Selesai")


class TanpaQueryPerBaris(DasarStatus):
    def test_dengan_status_bayar_tidak_query_lagi(self):
        for i in range(3):
            lunas = self.transaksi(T.STATUS_SELESAI)
            Pembayaran.objects.create(transaksi=lunas, total=0, metode=Pembayaran.METODE_CASH)
            self.bukti(self.transaksi(T.STATUS_SELESAI))
            self.transaksi(T.STATUS_SELESAI)
        daftar = list(T.dengan_status_bayar(T.objects.all()))
        with self.assertNumQueries(0):
            label = [t.status_tampil.label for t in daftar]
            label += [t.status_tampil_pelanggan.label for t in daftar]
        self.assertEqual(label.count("Selesai · Lunas"), 6)


class BadgeDiHalaman(DasarStatus):
    """Badge yang sama dipakai semua halaman; pelanggan memakai sudut pandangnya sendiri."""

    def setUp(self):
        super().setUp()
        self.selesai = self.transaksi(T.STATUS_SELESAI, mekanik=self.mekanik)
        self.diperiksa = self.transaksi(T.STATUS_MENUNGGU, mekanik=self.mekanik)

    def login(self, role, username):
        u = User.objects.create_user(username=username, password="x", role=role)
        self.client.force_login(u)
        return u

    def test_riwayat_pelanggan(self):
        self.client.force_login(self.pelanggan.user)
        r = self.client.get("/pelanggan/riwayat/")
        self.assertContains(r, "Selesai · Belum dibayar")
        self.assertContains(r, "Sedang diperiksa mekanik")
        # "Belum dibayar" hanya di badge, tidak lagi teks kecil terpisah.
        self.assertNotContains(r, '<span class="kecil merah">Belum dibayar</span>')

    def test_tanpa_query_per_baris(self):
        """Menambah baris Selesai (lunas, bukti diperiksa) tidak menambah query halaman."""
        halaman = [
            (self.pelanggan.user, "/pelanggan/riwayat/"),
            (self.pelanggan.user, "/pelanggan/dashboard/"),
            (self.login(User.ROLE_KASIR, "kasir"), "/kasir/transaksi/"),
            (self.mekanik.user, "/mekanik/pengerjaan/"),
            (self.login(User.ROLE_ADMIN, "admin"), "/adminpanel/dashboard/"),
        ]
        sebelum = [self._jumlah_query(u, url) for u, url in halaman]
        for i in range(3):
            lunas = self.transaksi(T.STATUS_SELESAI, mekanik=self.mekanik)
            Pembayaran.objects.create(transaksi=lunas, total=0, metode=Pembayaran.METODE_CASH)
            self.bukti(self.transaksi(T.STATUS_SELESAI, mekanik=self.mekanik))
        sesudah = [self._jumlah_query(u, url) for u, url in halaman]
        self.assertEqual(sesudah, sebelum)

    def _jumlah_query(self, user, url):
        self.client.force_login(user)
        with CaptureQueriesContext(connection) as q:
            self.assertEqual(self.client.get(url).status_code, 200)
        return len(q)

    def test_detail_riwayat_pelanggan(self):
        self.client.force_login(self.pelanggan.user)
        r = self.client.get(f"/pelanggan/riwayat/{self.selesai.pk}/")
        self.assertContains(r, 'class="badge-st merah">Selesai · Belum dibayar</span>')

    def test_beranda_pelanggan(self):
        self.client.force_login(self.pelanggan.user)
        r = self.client.get("/pelanggan/dashboard/")
        self.assertContains(r, "Sedang diperiksa mekanik")
        self.assertContains(r, "Selesai · Belum dibayar")

    def test_daftar_kasir(self):
        self.login(User.ROLE_KASIR, "kasir")
        r = self.client.get("/kasir/transaksi/")
        self.assertContains(r, "Selesai · Belum dibayar")
        self.assertContains(r, "Diperiksa mekanik")
        self.assertNotContains(r, "Sedang diperiksa mekanik")

    def test_pengerjaan_mekanik(self):
        self.client.force_login(self.mekanik.user)
        r = self.client.get("/mekanik/pengerjaan/")
        self.assertContains(r, "Diperiksa mekanik")
        self.assertContains(r, "Selesai · Belum dibayar")

    def test_dashboard_admin(self):
        self.login(User.ROLE_ADMIN, "admin")
        r = self.client.get("/adminpanel/dashboard/")
        self.assertContains(r, "Selesai · Belum dibayar")

    def test_laporan_admin_tetap_label_database(self):
        self.login(User.ROLE_ADMIN, "admin")
        r = self.client.get("/adminpanel/laporan/transaksi/")
        self.assertNotContains(r, "Selesai · Belum dibayar")
        self.assertContains(r, ">Selesai</span>")
