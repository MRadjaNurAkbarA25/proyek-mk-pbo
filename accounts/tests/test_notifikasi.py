"""Badge notifikasi di sidebar semua role, dan endpoint /accounts/notifikasi/ untuk pembaruan tanpa muat ulang."""
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from pembayaran.models import BuktiPembayaran, Pembayaran
from pembelian.models import PembelianSparepart, Supplier
from servis.models import PengajuanServis
from servis.models import TransaksiServis as T
from sparepart.models import Sparepart

NOTIF = "/accounts/notifikasi/"
GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00"
       b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


class Dasar(TestCase):
    def setUp(self):
        self.pel_user = User.objects.create_user(username="siti", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.pel_user)
        self.mek = self.buat_mekanik("andi")
        self.mek2 = self.buat_mekanik("budi")
        self.kasir = User.objects.create_user(username="kasir", password="x", role=User.ROLE_KASIR)
        self.admin = User.objects.create_user(username="adm", password="x", role=User.ROLE_ADMIN)
        self.nomor = 0

    def buat_mekanik(self, nama):
        return Mekanik.objects.create(user=User.objects.create_user(
            username=nama, password="x", role=User.ROLE_MEKANIK), status=Mekanik.STATUS_TERSEDIA)

    def motor(self):
        self.nomor += 1
        return Motor.objects.create(pelanggan=self.p, no_polisi=f"KT {self.nomor} A", merk="Honda",
                                    model_kendaraan="Beat", tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)

    def panggilan(self, mekanik):
        return T.buka(keterangan="Panggilan home service dikirim.", oleh=self.pel_user, pelanggan=self.p,
                      kendaraan=self.motor(), keluhan="Mogok", mekanik=mekanik,
                      tipe_layanan=T.TIPE_HOME_SERVICE, lokasi_servis="Jl. A",
                      status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK, kendaraan_hadir=False)

    def di_bengkel(self, **lain):
        return T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor(),
                      keluhan="Rem", **lain)

    def selesai_di_bengkel(self):
        t = self.di_bengkel()
        T.objects.filter(pk=t.pk).update(status=T.STATUS_SELESAI, total_biaya=Decimal("100000"))
        t.refresh_from_db()
        return t

    def angka(self, user, url):
        self.client.force_login(user)
        return self.client.get(url).context


class Mekanik_(Dasar):
    def test_panggilan_baru_hanya_untuk_mekanik_yang_dipanggil(self):
        t = self.panggilan(self.mek)
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_panggilan_hs"], 1)
        self.assertEqual(self.angka(self.mek2.user, "/mekanik/dashboard/")["jumlah_panggilan_hs"], 0)
        t.terima_home_service()
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_panggilan_hs"], 0)

    def test_panggilan_ditolak_padam(self):
        self.panggilan(self.mek).tolak_home_service()
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_panggilan_hs"], 0)

    def test_antrian_dan_tidak_tampil_saat_cuti(self):
        self.di_bengkel()
        self.di_bengkel(kendaraan_hadir=False)
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_antrian"], 1)
        Mekanik.objects.filter(pk=self.mek.pk).update(status=Mekanik.STATUS_CUTI)
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_antrian"], 0)

    def _menunggu_persetujuan(self):
        t = self.panggilan(self.mek)
        t.terima_home_service()
        t.input_diagnosis("Busi", "Ganti busi")
        # Detail dibuka mekanik saat menulis diagnosis.
        t.tandai_dibaca_mekanik()
        return t

    def test_jawaban_pelanggan_menyalakan_pengerjaan_lalu_padam(self):
        t = self._menunggu_persetujuan()
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_perlu_dilihat"], 0)
        T.objects.get(pk=t.pk).konfirmasi(True)
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_perlu_dilihat"], 1)
        self.assertEqual(self.angka(self.mek2.user, "/mekanik/dashboard/")["jumlah_perlu_dilihat"], 0)
        self.client.force_login(self.mek.user)
        self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_perlu_dilihat"], 0)

    def test_setuju_di_lokasi_tidak_dihitung(self):
        t = self._menunggu_persetujuan()
        t.konfirmasi_di_lokasi(self.mek)
        self.assertEqual(self.angka(self.mek.user, "/mekanik/dashboard/")["jumlah_perlu_dilihat"], 0)

    def test_pesan_pelanggan_tetap_dihitung_terpisah(self):
        t = self._menunggu_persetujuan()
        T.objects.get(pk=t.pk).konfirmasi(True)
        t.refresh_from_db()
        t.tulis_pesan_pelanggan(self.p, "Kira-kira selesai jam berapa?")
        k = self.angka(self.mek.user, "/mekanik/dashboard/")
        self.assertEqual(k["jumlah_pesan_pelanggan"], 1)
        self.assertEqual(k["jumlah_perlu_dilihat"], 1)

    def test_menu_mekanik_di_halaman_sparepart_sama(self):
        self.panggilan(self.mek)
        self.client.force_login(self.mek.user)
        for url in ("/mekanik/dashboard/", "/sparepart/"):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), 'data-badge="jumlah_panggilan_hs"')


class Stok(Dasar):
    def test_stok_kritis_dan_warnanya(self):
        Sparepart.objects.create(kode="A", nama="Aki", kategori="x", harga=1, stok=2, stok_minimum=5)
        k = self.angka(self.admin, "/adminpanel/dashboard/")
        self.assertEqual((k["jumlah_stok_kritis"], k["warna_stok_kritis"]), (1, "kuning"))
        Sparepart.objects.create(kode="B", nama="Busi", kategori="x", harga=1, stok=0, stok_minimum=5)
        for user, url in ((self.admin, "/adminpanel/dashboard/"), (self.kasir, "/kasir/dashboard/"),
                          (self.mek.user, "/mekanik/dashboard/")):
            with self.subTest(user=user.username):
                k = self.angka(user, url)
                self.assertEqual((k["jumlah_stok_kritis"], k["warna_stok_kritis"]), (2, "merah"))

    def test_pelanggan_tidak_mendapat_angka_stok(self):
        Sparepart.objects.create(kode="B", nama="Busi", kategori="x", harga=1, stok=0, stok_minimum=5)
        self.assertNotIn("jumlah_stok_kritis", self.angka(self.pel_user, "/pelanggan/dashboard/"))


class Admin(Dasar):
    def test_pembelian_draf(self):
        s = Supplier.objects.create(nama="PT A")
        PembelianSparepart.objects.create(supplier=s, dicatat_oleh=self.admin, metode_bayar=PembelianSparepart.METODE_CHOICES[0][0])
        self.assertEqual(self.angka(self.admin, "/adminpanel/dashboard/")["jumlah_pembelian_draf"], 1)
        self.assertNotIn("jumlah_pembelian_draf", self.angka(self.kasir, "/kasir/dashboard/"))


class Kasir(Dasar):
    def daftar(self, **kueri):
        self.client.force_login(self.kasir)
        return self.client.get("/kasir/transaksi/", kueri)

    def test_selesai_belum_dibayar_menyala_lalu_padam_setelah_cash(self):
        t = self.selesai_di_bengkel()
        self.assertEqual(self.daftar().context["jumlah_perlu_tindakan"], 1)
        Pembayaran.buat(t, Pembayaran.METODE_CASH, uang_dibayar=Decimal("100000"))
        self.assertEqual(self.daftar().context["jumlah_perlu_tindakan"], 0)

    def test_bukti_menunggu_tidak_dihitung(self):
        t = self.selesai_di_bengkel()
        BuktiPembayaran.objects.create(transaksi=t, jenis=BuktiPembayaran.JENIS_BANK, nama_penyedia="BRI",
                                       nomor_referensi="R1", berkas=SimpleUploadedFile("b.gif", GIF))
        self.assertEqual(self.daftar().context["jumlah_perlu_tindakan"], 0)

    def test_kendaraan_belum_tiba_dihitung(self):
        self.di_bengkel(kendaraan_hadir=False)
        self.assertEqual(self.daftar().context["jumlah_perlu_tindakan"], 1)

    def test_filter_perlu_tindakan_sama_dengan_angka(self):
        a = self.selesai_di_bengkel()
        b = self.di_bengkel(kendaraan_hadir=False)
        self.di_bengkel()  # sudah di bengkel, belum selesai: tidak perlu tindakan kasir
        r = self.daftar(perlu="1")
        self.assertEqual({t.pk for t in r.context["transaksi_list"]}, {a.pk, b.pk})
        self.assertEqual(r.context["jumlah_hasil"], r.context["jumlah_perlu_tindakan"])
        self.assertContains(self.daftar(), "?perlu=1")


class Pelanggan_(Dasar):
    def test_pengajuan_ditolak_menyala_lalu_padam_setelah_dibuka(self):
        pj = PengajuanServis.objects.create(pelanggan=self.p, kendaraan=self.motor(), keluhan="Rem bunyi")
        self.assertEqual(self.angka(self.pel_user, "/pelanggan/dashboard/")["jumlah_pengajuan_ditolak"], 0)
        pj.tolak(self.kasir, "Bengkel penuh")
        self.assertEqual(self.angka(self.pel_user, "/pelanggan/dashboard/")["jumlah_pengajuan_ditolak"], 1)
        self.client.get("/pelanggan/pengajuan-saya/")
        self.assertEqual(self.angka(self.pel_user, "/pelanggan/dashboard/")["jumlah_pengajuan_ditolak"], 0)

    def test_kartu_tagihan_di_beranda(self):
        self.client.force_login(self.pel_user)
        self.assertNotContains(self.client.get("/pelanggan/dashboard/"), "Tagihan menunggu pembayaran")
        t = self.selesai_di_bengkel()
        r = self.client.get("/pelanggan/dashboard/")
        self.assertContains(r, "Tagihan menunggu pembayaran")
        self.assertContains(r, f"/pelanggan/riwayat/{t.pk}/")
        Pembayaran.buat(t, Pembayaran.METODE_CASH, uang_dibayar=Decimal("100000"))
        self.assertNotContains(self.client.get("/pelanggan/dashboard/"), "Tagihan menunggu pembayaran")


class Endpoint(Dasar):
    def setUp(self):
        super().setUp()
        self.panggilan(self.mek)
        self.selesai_di_bengkel()
        Sparepart.objects.create(kode="B", nama="Busi", kategori="x", harga=1, stok=0, stok_minimum=5)

    def test_angka_sama_dengan_context_processor(self):
        for user, url in ((self.kasir, "/kasir/dashboard/"), (self.admin, "/adminpanel/dashboard/"),
                          (self.mek.user, "/mekanik/dashboard/"), (self.pel_user, "/pelanggan/dashboard/")):
            with self.subTest(user=user.username):
                konteks = self.angka(user, url)
                data = self.client.get(NOTIF).json()
                self.assertTrue(data)
                for nama, nilai in data.items():
                    self.assertEqual(konteks[nama], nilai, nama)

    def test_belum_login_ditolak(self):
        self.assertIn(self.client.get(NOTIF).status_code, (401, 403))

    def test_role_lain_tidak_melihat_angka_role_lain(self):
        self.client.force_login(self.pel_user)
        data = self.client.get(NOTIF).json()
        for nama in ("jumlah_panggilan_hs", "jumlah_perlu_tindakan", "jumlah_stok_kritis", "jumlah_bukti_menunggu"):
            self.assertNotIn(nama, data)
        self.client.force_login(self.mek2.user)
        data = self.client.get(NOTIF).json()
        self.assertEqual(data["jumlah_panggilan_hs"], 0)
        self.assertNotIn("jumlah_perlu_tindakan", data)

    def test_skrip_hanya_di_halaman_berlogin(self):
        self.assertNotContains(self.client.get("/"), "js/notifikasi.js")
        self.assertNotContains(self.client.get("/accounts/login/"), "js/notifikasi.js")
        for user, url in ((self.kasir, "/kasir/dashboard/"), (self.mek.user, "/mekanik/dashboard/"),
                          (self.pel_user, "/pelanggan/dashboard/")):
            self.client.force_login(user)
            self.assertContains(self.client.get(url), "js/notifikasi.js")


class JumlahQuery(Dasar):
    """Badge menambah beberapa query per halaman, tidak boleh melonjak per baris data."""

    def test_query_tidak_melonjak(self):
        for _ in range(5):
            self.panggilan(self.mek)
            self.selesai_di_bengkel()
        for user, url, batas in ((self.kasir, "/kasir/dashboard/", 40), (self.admin, "/adminpanel/dashboard/", 40),
                                 (self.mek.user, "/mekanik/dashboard/", 45), (self.pel_user, "/pelanggan/dashboard/", 40)):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.client.get(url)
                self.assertLessEqual(self._hitung(url), batas)

    def _hitung(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as q:
            self.client.get(url)
        return len(q)
