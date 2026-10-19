"""Kelola Kasir, dan menonaktifkan akun alih-alih menghapus.

Dulu akun kasir hanya bisa dibuat lewat /admin/ bawaan Django atau
createsuperuser. Sekarang admin punya halaman Kelola Kasir: tambah, ubah,
dan nonaktifkan. Tidak ada hapus, sama seperti keputusan untuk pelanggan.

Alasannya sama untuk kasir dan mekanik: nama mereka tercatat di riwayat
(pengajuan yang diproses, linimasa, transaksi yang dikerjakan, laporan
kinerja). Menghapus akun mengosongkan semua jejak itu (on_delete=SET_NULL).
Akun yang dinonaktifkan tidak bisa login, tapi jejaknya utuh.

Mekanik yang belum pernah memegang transaksi tetap boleh dihapus, supaya
salah input bisa diperbaiki.
"""
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis as T


class DasarAkun(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin9", password="x", role=User.ROLE_ADMIN)
        self.kasir = User.objects.create_user(
            username="kasir9", password="RahasiaKasir#2026", role=User.ROLE_KASIR, first_name="Wati")
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        mu = User.objects.create_user(username="mek9", password="x", role=User.ROLE_MEKANIK)
        self.mek = Mekanik.objects.create(user=mu, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda",
            model_kendaraan="Beat", tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)
        self.client.force_login(self.admin)


class KelolaKasir(DasarAkun):
    def test_admin_menambah_kasir_yang_bisa_login(self):
        respons = self.client.post("/adminpanel/kasir/tambah/", {
            "nama_lengkap": "Rina Kasir", "username": "rina", "email": "rina@bengkel.id",
            "no_telepon": "0812", "password1": "KataSandiKuat#77", "password2": "KataSandiKuat#77",
        })
        self.assertEqual(respons.status_code, 302)
        rina = User.objects.get(username="rina")
        self.assertEqual(rina.role, User.ROLE_KASIR)
        self.assertTrue(self.client.login(username="rina", password="KataSandiKuat#77"))

    def test_username_ganda_ditolak(self):
        respons = self.client.post("/adminpanel/kasir/tambah/", {
            "nama_lengkap": "X", "username": "KASIR9", "email": "",
            "password1": "KataSandiKuat#77", "password2": "KataSandiKuat#77",
        })
        self.assertEqual(respons.status_code, 200)
        self.assertEqual(User.objects.filter(username__iexact="kasir9").count(), 1)

    def test_kata_sandi_lemah_ditolak(self):
        respons = self.client.post("/adminpanel/kasir/tambah/", {
            "nama_lengkap": "X", "username": "lemah", "email": "",
            "password1": "123", "password2": "123",
        })
        self.assertEqual(respons.status_code, 200)
        self.assertFalse(User.objects.filter(username="lemah").exists())

    def test_daftar_hanya_berisi_kasir(self):
        isi = self.client.get("/adminpanel/kasir/").content.decode()
        # Hanya isi tabel: nama admin yang login memang tampil di pojok atas.
        tabel = isi.split("<tbody>")[1].split("</tbody>")[0]
        self.assertIn("kasir9", tabel)
        self.assertNotIn("mek9", tabel)
        self.assertNotIn("admin9", tabel)

    def test_ubah_data_dan_ganti_kata_sandi(self):
        self.client.post(f"/adminpanel/kasir/{self.kasir.pk}/ubah/", {
            "nama_lengkap": "Wati Lestari", "email": "wati@bengkel.id", "no_telepon": "",
            "password1": "SandiBaruWati#9", "password2": "SandiBaruWati#9",
        })
        self.kasir.refresh_from_db()
        self.assertEqual(self.kasir.first_name, "Wati Lestari")
        self.assertTrue(self.kasir.check_password("SandiBaruWati#9"))

    def test_ubah_tanpa_kata_sandi_tidak_mengganti_sandi(self):
        self.client.post(f"/adminpanel/kasir/{self.kasir.pk}/ubah/", {
            "nama_lengkap": "Wati", "email": "", "no_telepon": "", "password1": "", "password2": "",
        })
        self.kasir.refresh_from_db()
        self.assertTrue(self.kasir.check_password("RahasiaKasir#2026"))

    def test_halaman_ubah_tidak_bisa_dipakai_untuk_akun_lain(self):
        """URL kasir tidak boleh bisa mengubah admin atau pelanggan."""
        self.assertEqual(self.client.get(f"/adminpanel/kasir/{self.admin.pk}/ubah/").status_code, 404)
        self.assertEqual(self.client.get(f"/adminpanel/kasir/{self.user.pk}/ubah/").status_code, 404)

    def test_hanya_admin(self):
        self.client.force_login(self.kasir)
        respons = self.client.get("/adminpanel/kasir/")
        self.assertNotEqual(respons.status_code, 200)

    def test_menu_kelola_kasir_ada_di_sidebar_admin(self):
        self.assertContains(self.client.get("/adminpanel/dashboard/"), "/adminpanel/kasir/")


class NonaktifkanAkun(DasarAkun):
    def url(self, user):
        return f"/adminpanel/akun/{user.pk}/status/"

    def test_kasir_nonaktif_tidak_bisa_login_dan_sesi_lamanya_putus(self):
        kasir_client = self.client_class()
        kasir_client.force_login(self.kasir)

        self.client.post(self.url(self.kasir), {"aktif": "0"})
        self.kasir.refresh_from_db()
        self.assertFalse(self.kasir.is_active)
        self.assertFalse(self.client.login(username="kasir9", password="RahasiaKasir#2026"))
        respons = kasir_client.get("/kasir/dashboard/")
        self.assertNotEqual(respons.status_code, 200, "sesi yang sudah login ikut putus")

    def test_jejak_kasir_tetap_utuh(self):
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.p, kendaraan=self.motor, keluhan="Oli bocor")
        pengajuan.terima(self.kasir)
        self.client.post(self.url(self.kasir), {"aktif": "0"})
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.diproses_oleh, self.kasir)

    def test_bisa_diaktifkan_lagi(self):
        self.client.post(self.url(self.kasir), {"aktif": "0"})
        self.client.post(self.url(self.kasir), {"aktif": "1"})
        self.kasir.refresh_from_db()
        self.assertTrue(self.kasir.is_active)

    def test_admin_dan_pelanggan_tidak_bisa_dinonaktifkan_dari_sini(self):
        for akun in (self.admin, self.user):
            self.client.post(self.url(akun), {"aktif": "0"})
            akun.refresh_from_db()
            self.assertTrue(akun.is_active, akun.username)

    def test_mekanik_nonaktif_jadi_cuti_dan_tidak_bisa_dipilih(self):
        self.client.post(self.url(self.mek.user), {"aktif": "0"})
        self.mek.refresh_from_db()
        self.mek.user.refresh_from_db()
        self.assertFalse(self.mek.user.is_active)
        self.assertEqual(self.mek.status, Mekanik.STATUS_CUTI)

        self.mek.perbarui_status_otomatis()
        self.mek.refresh_from_db()
        self.assertEqual(self.mek.status, Mekanik.STATUS_CUTI, "tidak boleh hidup lagi sendiri")

    def test_mekanik_dengan_pekerjaan_berjalan_tidak_bisa_dinonaktifkan(self):
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        t.ambil_oleh(self.mek)
        t.save()
        self.client.post(self.url(self.mek.user), {"aktif": "0"})
        self.mek.user.refresh_from_db()
        self.assertTrue(self.mek.user.is_active)

    def test_mekanik_diaktifkan_lagi_kembali_tersedia(self):
        self.client.post(self.url(self.mek.user), {"aktif": "0"})
        self.client.post(self.url(self.mek.user), {"aktif": "1"})
        self.mek.refresh_from_db()
        self.assertEqual(self.mek.status, Mekanik.STATUS_TERSEDIA)


class HapusMekanik(DasarAkun):
    def url(self):
        return f"/mekanik/kelola/{self.mek.pk}/hapus/"

    def test_mekanik_dengan_riwayat_tidak_bisa_dihapus(self):
        """Dulu bisa, dan namanya hilang dari riwayat pelanggan serta laporan kinerja."""
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        t.ambil_oleh(self.mek)
        t.save()
        t.input_diagnosis("a", "b")
        t.konfirmasi(True)
        t.selesaikan()

        respons = self.client.post(self.url(), follow=True)
        self.assertTrue(Mekanik.objects.filter(pk=self.mek.pk).exists())
        t.refresh_from_db()
        self.assertEqual(t.mekanik_id, self.mek.pk)
        self.assertContains(respons, "Nonaktifkan")

    def test_mekanik_tanpa_riwayat_tetap_bisa_dihapus(self):
        self.client.post(self.url())
        self.assertFalse(Mekanik.objects.filter(pk=self.mek.pk).exists())


class TandaiTibaHanyaUntukYangMenunggu(DasarAkun):
    def test_home_service_tidak_bisa_ditandai_tiba_lewat_url(self):
        """Tombolnya memang tidak tampil, tapi POST langsung dulu diterima."""
        t = T.buka(keterangan="x", oleh=self.user, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="Mogok", mekanik=self.mek, tipe_layanan=T.TIPE_HOME_SERVICE,
                   lokasi_servis="Jl. A", status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
                   kendaraan_hadir=False)
        self.client.force_login(self.kasir)
        self.client.post(f"/kasir/transaksi/{t.pk}/tiba/")
        t.refresh_from_db()
        self.assertFalse(t.kendaraan_hadir)
