"""Detail Riwayat Servis pelanggan: tata letak dan kontak (QoL A1, A3).

A1: linimasa pindah ke kolom kanan, seperti halaman mekanik dan kasir.
A3: nama mekanik selalu tampil. Nomor yang diberikan ke pelanggan:
    - servis di bengkel  -> nomor resmi bengkel (bukan nomor pribadi kasir);
    - home service yang sudah diterima mekanik dan belum selesai -> nomor
      mekanik, karena mekaniknya sedang menuju / berada di lokasi pelanggan;
    - selain itu (belum diterima, selesai, batal) -> nomor bengkel lagi.
Aturannya di TransaksiServis.kontak_mekanik_terbuka, bukan di template.
"""
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from landing.context_processors import info_bengkel
from servis.models import TransaksiServis as T

NOMOR_BENGKEL = info_bengkel(None)["telepon_bengkel"]
NOMOR_MEKANIK = "0812-3456-7890"


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(
            username="kasir", password="x", role=User.ROLE_KASIR, no_telepon="0899-1111-2222")
        mu = User.objects.create_user(username="mek", password="x", role=User.ROLE_MEKANIK,
                                      first_name="Andi", no_telepon=NOMOR_MEKANIK)
        self.mek = Mekanik.objects.create(user=mu, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda", model_kendaraan="Beat",
            tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)
        self.client.force_login(self.user)

    def di_bengkel(self):
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="Rem bunyi", tipe_layanan=T.TIPE_DI_BENGKEL)
        t.ambil_oleh(self.mek)
        t.save()
        return t

    def home_service(self):
        return T.buka(keterangan="x", oleh=self.user, pelanggan=self.p, kendaraan=self.motor,
                      keluhan="Mogok", mekanik=self.mek, tipe_layanan=T.TIPE_HOME_SERVICE,
                      lokasi_servis="Jl. Mawar 10", status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
                      kendaraan_hadir=False)

    def buka(self, t):
        return self.client.get(f"/pelanggan/riwayat/{t.pk}/")


class AturanKontak(Dasar):
    def test_di_bengkel_tidak_membuka_nomor_mekanik(self):
        self.assertFalse(self.di_bengkel().kontak_mekanik_terbuka)

    def test_home_service_belum_diterima(self):
        self.assertFalse(self.home_service().kontak_mekanik_terbuka)

    def test_home_service_sudah_diterima(self):
        t = self.home_service()
        t.terima_home_service()
        self.assertTrue(t.kontak_mekanik_terbuka)

    def test_home_service_selesai_atau_batal(self):
        t = self.home_service()
        t.terima_home_service()
        for status in (T.STATUS_SELESAI, T.STATUS_DIBATALKAN):
            t.status = status
            self.assertFalse(t.kontak_mekanik_terbuka, status)


class HalamanDetail(Dasar):
    def test_di_bengkel_memakai_nomor_bengkel(self):
        r = self.buka(self.di_bengkel())
        self.assertContains(r, "Andi")
        self.assertContains(r, NOMOR_BENGKEL)
        self.assertNotContains(r, NOMOR_MEKANIK)
        self.assertNotContains(r, "0899-1111-2222")

    def test_home_service_berjalan_memakai_nomor_mekanik(self):
        t = self.home_service()
        t.terima_home_service()
        r = self.buka(t)
        self.assertContains(r, NOMOR_MEKANIK)
        self.assertContains(r, "https://wa.me/6281234567890")
        self.assertContains(r, 'href="tel:+6281234567890"')

    def test_mekanik_tanpa_nomor_jatuh_ke_nomor_bengkel(self):
        User.objects.filter(pk=self.mek.user.pk).update(no_telepon="")
        t = self.home_service()
        t.terima_home_service()
        r = self.buka(t)
        self.assertContains(r, NOMOR_BENGKEL)

    def test_belum_ada_mekanik(self):
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
                   keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        self.assertContains(self.buka(t), "Belum ditentukan")

    def test_linimasa_di_kolom_kanan(self):
        isi = self.buka(self.di_bengkel()).content.decode()
        samping = isi.index('class="dtl-samping"')
        self.assertGreater(isi.index('class="linimasa"'), samping)
        self.assertGreater(isi.index("<h3>Layanan</h3>"), isi.index('class="dtl-utama"'))
        self.assertLess(isi.index("<h3>Layanan</h3>"), samping)

    def test_linimasa_tanpa_query_per_baris(self):
        t = self.di_bengkel()
        t.input_diagnosis("Kampas aus", "Ganti kampas")
        self.buka(t)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as sedikit:
            self.buka(t)
        t.konfirmasi(True)
        t.tulis_pembaruan(self.mek, "Menunggu kampas datang.")
        t.tulis_pembaruan(self.mek, "Kampas sudah datang.")
        with CaptureQueriesContext(connection) as banyak:
            self.buka(t)
        self.assertEqual(len(sedikit), len(banyak))


class TampilanSamaDenganMekanik(Dasar):
    """Susunan dua kolom disalin dari Detail Servis mekanik dan harus tetap sama."""

    def aturan(self, berkas, pemilih):
        from django.contrib.staticfiles import finders
        import re
        with open(finders.find(berkas), encoding="utf-8") as f:
            css = f.read()
        cocok = re.search(re.escape(pemilih) + r"\s*\{([^}]*)\}", css)
        self.assertIsNotNone(cocok, f"{pemilih} tidak ada di {berkas}")
        return " ".join(cocok.group(1).split())

    def test_aturan_dua_kolom_sama_dengan_mekanik(self):
        for pemilih in (".dtl-grid", ".dtl-utama, .dtl-samping", ".dtl-data > div", ".dtl-data dt"):
            self.assertEqual(self.aturan("css/riwayat.css", pemilih),
                             self.aturan("css/mekanik.css", pemilih), pemilih)

    def test_titik_lipat_sama_dengan_mekanik(self):
        from django.contrib.staticfiles import finders
        with open(finders.find("css/riwayat.css"), encoding="utf-8") as f:
            css = " ".join(f.read().split())
        self.assertIn("@media (max-width: 1000px) { .dtl-grid { grid-template-columns: 1fr; } }", css)

    def test_memuat_riwayat_css_tanpa_bootstrap(self):
        r = self.buka(self.di_bengkel())
        self.assertContains(r, "css/riwayat.css")
        self.assertContains(r, 'class="dtl-grid"')
        self.assertNotContains(r, 'class="card ')

    def test_format_rupiah(self):
        from pelanggan.templatetags.angka import rupiah
        self.assertEqual(rupiah(1250000), "Rp 1.250.000,00")
        self.assertEqual(rupiah("50000.00"), "Rp 50.000,00")
        self.assertEqual(rupiah("67000.5"), "Rp 67.000,50")
        self.assertEqual(rupiah(-1500), "-Rp 1.500,00")
        self.assertEqual(rupiah(None), "Rp 0,00")
        self.assertEqual(rupiah(0), "Rp 0,00")
        self.assertEqual(rupiah("bukan angka"), "Rp 0,00")
