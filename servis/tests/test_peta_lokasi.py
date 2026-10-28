"""Peta OpenStreetMap: titik lokasi home service dan alamat profil, serta tombol buka di Google Maps."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from bengkel_project.lokasi import titik_dari
from kendaraan.models import Motor
from servis.models import TransaksiServis as T

HOME = "/pelanggan/home-service/pesan/"
PROFIL = "/accounts/profil/"


class TitikDari(SimpleTestCase):
    def test_titik_valid(self):
        self.assertEqual(titik_dari("-0.502106", "117.153709"), (Decimal("-0.502106"), Decimal("117.153709")))

    def test_dibulatkan_enam_desimal(self):
        self.assertEqual(titik_dari("-0.50210612345", "117.1537"), (Decimal("-0.502106"), Decimal("117.153700")))

    def test_di_luar_indonesia_atau_bukan_angka_diabaikan(self):
        for lat, lng in (("51.5", "-0.12"), ("-0.5", "150"), ("abc", "117"), ("", "117.1"), (None, None), ("nan", "117")):
            with self.subTest(lat=lat, lng=lng):
                self.assertEqual(titik_dari(lat, lng), (None, None))


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="siti", password="x", role=User.ROLE_PELANGGAN,
                                             first_name="Siti", email="siti@contoh.id", no_telepon="0812",
                                             alamat="Jl. Contoh 1, Samarinda")
        self.p = Pelanggan.objects.create(user=self.user)
        self.mek = Mekanik.objects.create(user=User.objects.create_user(
            username="m", password="x", role=User.ROLE_MEKANIK, first_name="Andi"),
            status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda", model_kendaraan="Beat",
            tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)

    def data_home(self, **ubah):
        data = {"kendaraan": f"motor:{self.motor.pk}", "mekanik": self.mek.pk, "keluhan": "Mesin mogok",
                "lokasi_servis": "Jl. Contoh 1, Samarinda", "lokasi_lat": "-0.470000", "lokasi_lng": "117.157000"}
        data.update(ubah)
        return data

    def home_service(self, lat=None, lng=None, lokasi="Jl. Contoh 1"):
        return T.buka(keterangan="x", pelanggan=self.p, kendaraan=self.motor, keluhan="Mogok",
                      mekanik=self.mek, tipe_layanan=T.TIPE_HOME_SERVICE, lokasi_servis=lokasi,
                      lokasi_lat=lat, lokasi_lng=lng,
                      status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK, kendaraan_hadir=False)


class SimpanTitik(Dasar):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_home_service_menyimpan_titik_valid(self):
        self.client.post(HOME, self.data_home())
        t = T.objects.get()
        self.assertEqual((t.lokasi_lat, t.lokasi_lng), (Decimal("-0.470000"), Decimal("117.157000")))

    def test_titik_tidak_sah_diabaikan_tanpa_error(self):
        for lat, lng in (("48.85", "2.35"), ("bukan", "angka")):
            with self.subTest(lat=lat):
                T.objects.all().delete()
                r = self.client.post(HOME, self.data_home(lokasi_lat=lat, lokasi_lng=lng))
                self.assertEqual(r.status_code, 302)
                t = T.objects.get()
                self.assertIsNone(t.lokasi_lat)
                self.assertIsNone(t.lokasi_lng)

    def test_tanpa_titik_tetap_tersimpan(self):
        r = self.client.post(HOME, self.data_home(lokasi_lat="", lokasi_lng=""))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(T.objects.get().lokasi_servis, "Jl. Contoh 1, Samarinda")

    def test_profil_menyimpan_dan_mengabaikan_titik(self):
        data = {"aksi": "profil", "nama_lengkap": "Siti", "email": "siti@contoh.id", "no_telepon": "0812",
                "alamat": "Jl. Baru 2", "jenis_kelamin": "", "alamat_lat": "-0.47", "alamat_lng": "117.15"}
        self.client.post(PROFIL, data)
        self.user.refresh_from_db()
        self.assertEqual((self.user.alamat_lat, self.user.alamat_lng), (Decimal("-0.470000"), Decimal("117.150000")))
        self.client.post(PROFIL, {**data, "alamat_lat": "999", "alamat_lng": "999"})
        self.user.refresh_from_db()
        self.assertIsNone(self.user.alamat_lat)
        self.assertEqual(self.user.alamat, "Jl. Baru 2")

    def test_home_service_terisi_awal_dari_profil(self):
        User.objects.filter(pk=self.user.pk).update(alamat_lat=Decimal("-0.471"), alamat_lng=Decimal("117.158"))
        form = self.client.get(HOME).context["form"]
        self.assertEqual(form["lokasi_servis"].value(), "Jl. Contoh 1, Samarinda")
        self.assertEqual(str(form["lokasi_lat"].value()), "-0.471000")
        self.assertEqual(str(form["lokasi_lng"].value()), "117.158000")


class UrlPeta(Dasar):
    def test_dengan_titik(self):
        t = self.home_service(Decimal("-0.470000"), Decimal("117.157000"))
        self.assertEqual(t.url_peta_lokasi, "https://www.google.com/maps/search/?api=1&query=-0.470000,117.157000")

    def test_tanpa_titik_memakai_alamat(self):
        t = self.home_service(lokasi="Jl. Mawar 10, Samarinda")
        self.assertEqual(t.url_peta_lokasi, "https://www.google.com/maps/search/?api=1&query=Jl.+Mawar+10%2C+Samarinda")

    def test_bukan_home_service(self):
        t = T.buka(keterangan="x", pelanggan=self.p, kendaraan=self.motor, keluhan="Rem")
        self.assertIsNone(t.url_peta_lokasi)

    def test_pindah_ke_bengkel_tetap_menyimpan_titik_asal(self):
        t = self.home_service(Decimal("-0.470000"), Decimal("117.157000"))
        t.terima_home_service()
        t.lanjutkan_di_bengkel(timezone.localdate() + timedelta(days=1))
        t.refresh_from_db()
        self.assertIn("query=-0.470000,117.157000", t.url_peta_lokasi)


class TampilanPeta(Dasar):
    def test_detail_mekanik_home_service_ada_peta_dan_tombol(self):
        t = self.home_service(Decimal("-0.470000"), Decimal("117.157000"))
        self.client.force_login(self.mek.user)
        r = self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertContains(r, "Buka di Google Maps")
        self.assertContains(r, 'class="peta-tampil')
        self.assertContains(r, 'target="_blank" rel="noopener"')

    def test_detail_mekanik_servis_bengkel_tanpa_peta(self):
        t = T.buka(keterangan="x", pelanggan=self.p, kendaraan=self.motor, keluhan="Rem")
        t.ambil_oleh(self.mek)
        self.client.force_login(self.mek.user)
        r = self.client.get(f"/mekanik/servis/{t.pk}/")
        self.assertNotContains(r, "Buka di Google Maps")

    def test_kasir_dan_riwayat_pelanggan_menampilkan_tombol(self):
        t = self.home_service(lokasi="Jl. Mawar 10")
        self.client.force_login(self.user)
        self.assertContains(self.client.get(f"/pelanggan/riwayat/{t.pk}/"), "Buka di Google Maps")
        self.client.force_login(User.objects.create_user(username="k", password="x", role=User.ROLE_KASIR))
        self.assertContains(self.client.get(f"/kasir/transaksi/{t.pk}/"), "Buka di Google Maps")

    def test_hanya_home_service_dan_profil_yang_memuat_peta_interaktif(self):
        admin = User.objects.create_user(username="adm", password="x", role=User.ROLE_ADMIN)
        halaman = [
            (self.user, HOME, True), (self.user, PROFIL, True), (self.mek.user, PROFIL, True),
            (self.user, "/pelanggan/ajukan-servis/", False), (self.user, "/pelanggan/dashboard/", False),
            (admin, PROFIL, False), (admin, f"/adminpanel/pelanggan/{self.p.pk}/ubah/", False),
        ]
        for user, url, harap in halaman:
            with self.subTest(user=user.username, url=url):
                self.client.force_login(user)
                isi = self.client.get(url).content.decode()
                self.assertEqual("vendor/leaflet/leaflet.js" in isi, harap)
                self.assertEqual("js/peta-lokasi.js" in isi, harap)

    def test_leaflet_tersimpan_di_repo(self):
        for berkas in ("vendor/leaflet/leaflet.js", "vendor/leaflet/leaflet.css",
                       "vendor/leaflet/images/marker-icon.png", "vendor/leaflet/LICENSE"):
            self.assertIsNotNone(finders.find(berkas), berkas)
