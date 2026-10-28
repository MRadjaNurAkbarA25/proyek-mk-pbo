"""Persetujuan diagnosis di lokasi (home service) dan penanda asal home service."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PembaruanServis as P
from servis.models import TransaksiServis as T


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.mek = Mekanik.objects.create(user=User.objects.create_user(
            username="m", password="x", role=User.ROLE_MEKANIK, first_name="Andi"),
            status=Mekanik.STATUS_TERSEDIA)
        self.mek_lain = Mekanik.objects.create(user=User.objects.create_user(
            username="m2", password="x", role=User.ROLE_MEKANIK), status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda", model_kendaraan="Beat",
            tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)

    def home_service(self, diagnosis=True):
        t = T.buka(keterangan="Panggilan home service dikirim ke mekanik Andi.", oleh=self.user,
                   pelanggan=self.p, kendaraan=self.motor, keluhan="Mogok", mekanik=self.mek,
                   tipe_layanan=T.TIPE_HOME_SERVICE, lokasi_servis="Jl. Mawar 10",
                   status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK, kendaraan_hadir=False)
        t.terima_home_service()
        if diagnosis:
            t.input_diagnosis("Busi mati", "Ganti busi")
        return t

    def di_bengkel_menunggu_konfirmasi(self):
        t = T.buka(keterangan="x", pelanggan=self.p, kendaraan=self.motor, keluhan="Rem")
        t.ambil_oleh(self.mek)
        t.input_diagnosis("Kampas habis", "Ganti kampas")
        return t

    def baris_perbaikan(self, t):
        return P.objects.filter(transaksi=t, tahap=P.TAHAP_PERBAIKAN)


class SetujuDiLokasi(Dasar):
    def test_berhasil_untuk_home_service_dan_dicatat_oleh_mekanik(self):
        t = self.home_service()
        t.konfirmasi_di_lokasi(self.mek)
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_DIKERJAKAN)
        self.assertTrue(t.konfirmasi_pelanggan)
        baris = self.baris_perbaikan(t).get()
        self.assertEqual(baris.keterangan, "Diagnosis disetujui pelanggan langsung di lokasi.")
        self.assertEqual(baris.oleh, self.mek.user)

    def test_ditolak_untuk_servis_di_bengkel(self):
        t = self.di_bengkel_menunggu_konfirmasi()
        with self.assertRaises(ValidationError):
            t.konfirmasi_di_lokasi(self.mek)
        t.refresh_from_db()
        self.assertEqual(t.status, T.STATUS_MENUNGGU_KONFIRMASI)

    def test_ditolak_untuk_mekanik_lain(self):
        t = self.home_service()
        with self.assertRaises(ValidationError):
            t.konfirmasi_di_lokasi(self.mek_lain)
        self.assertFalse(self.baris_perbaikan(t).exists())

    def test_ditolak_untuk_status_lain(self):
        t = self.home_service(diagnosis=False)
        with self.assertRaises(ValidationError):
            t.konfirmasi_di_lokasi(self.mek)
        self.assertEqual(T.objects.get(pk=t.pk).status, T.STATUS_MENUNGGU)

    def test_pelanggan_dan_mekanik_bersamaan_hanya_satu_baris_perbaikan(self):
        t = self.home_service()
        salinan_pelanggan = T.objects.get(pk=t.pk)
        salinan_mekanik = T.objects.get(pk=t.pk)
        salinan_pelanggan.konfirmasi(True)
        with self.assertRaises(ValidationError):
            salinan_mekanik.konfirmasi_di_lokasi(self.mek)
        self.assertEqual(self.baris_perbaikan(t).count(), 1)
        self.assertEqual(self.baris_perbaikan(t).get().oleh, self.user)

    def test_pelanggan_tetap_bisa_menyetujui_sendiri(self):
        t = self.home_service()
        t.konfirmasi(True)
        self.assertEqual(self.baris_perbaikan(t).get().oleh, self.user)


class TombolDiDetailMekanik(Dasar):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.mek.user)

    def test_tombol_tampil_untuk_home_service_menunggu_konfirmasi(self):
        t = self.home_service()
        r = self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertContains(r, "Pelanggan setuju di lokasi")
        self.assertContains(r, f"/mekanik/servis/{t.pk}/setuju-di-lokasi/")
        self.assertContains(r, "data-konfirmasi=")

    def test_tombol_tidak_tampil_untuk_servis_bengkel(self):
        t = self.di_bengkel_menunggu_konfirmasi()
        r = self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertNotContains(r, "Pelanggan setuju di lokasi")

    def test_post_menyetujui(self):
        t = self.home_service()
        r = self.client.post(f"/mekanik/servis/{t.pk}/setuju-di-lokasi/")
        self.assertRedirects(r, f"/mekanik/servis/{t.pk}/", fetch_redirect_response=False)
        self.assertEqual(T.objects.get(pk=t.pk).status, T.STATUS_DIKERJAKAN)

    def test_post_mekanik_lain_404(self):
        t = self.home_service()
        self.client.force_login(self.mek_lain.user)
        self.assertEqual(self.client.post(f"/mekanik/servis/{t.pk}/setuju-di-lokasi/").status_code, 404)


class AsalHomeService(Dasar):
    def test_buka_home_service_menandai(self):
        self.assertTrue(self.home_service().berawal_home_service)

    def test_servis_bengkel_tidak_ditandai(self):
        self.assertFalse(self.di_bengkel_menunggu_konfirmasi().berawal_home_service)

    def test_tetap_true_setelah_lanjut_di_bengkel(self):
        t = self.home_service()
        t.lanjutkan_di_bengkel(timezone.localdate() + timedelta(days=1))
        t.refresh_from_db()
        self.assertEqual(t.tipe_layanan, T.TIPE_DI_BENGKEL)
        self.assertTrue(t.berawal_home_service)


class LaporanTransaksi(Dasar):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.create_user(username="adm", password="x", role=User.ROLE_ADMIN))

    def test_label_dan_angka_home_service(self):
        pindah = self.home_service()
        pindah.lanjutkan_di_bengkel(timezone.localdate() + timedelta(days=1))
        mobil_lain = Motor.objects.create(pelanggan=self.p, no_polisi="KT 2 B", merk="Yamaha",
                                          model_kendaraan="Mio", tahun=2019, jenis_motor="Matic",
                                          kapasitas_mesin=110)
        T.buka(keterangan="x", pelanggan=self.p, kendaraan=mobil_lain, keluhan="Oli",
               mekanik=self.mek_lain, tipe_layanan=T.TIPE_HOME_SERVICE, lokasi_servis="Jl. A",
               status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK, kendaraan_hadir=False)
        motor3 = Motor.objects.create(pelanggan=self.p, no_polisi="KT 3 C", merk="Honda",
                                      model_kendaraan="Vario", tahun=2021, jenis_motor="Matic",
                                      kapasitas_mesin=125)
        T.buka(keterangan="x", pelanggan=self.p, kendaraan=motor3, keluhan="Rem")

        r = self.client.get("/adminpanel/laporan/transaksi/")
        self.assertEqual(r.context["ringkasan"]["home_service"], 2)
        self.assertContains(r, "dari home service", count=1)
