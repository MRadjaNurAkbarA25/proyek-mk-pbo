"""Pelanggan tanpa kendaraan: keadaan kosong + instruksi, lalu kembali ke form asal setelah menambah kendaraan."""
from urllib.parse import quote

from django.contrib.messages import get_messages
from django.test import TestCase

from accounts.models import Pelanggan, User
from kendaraan.models import Motor

AJUKAN = "/pelanggan/ajukan-servis/"
HOME = "/pelanggan/home-service/pesan/"
BERANDA = "/pelanggan/dashboard/"
GARASI = "/pelanggan/kendaraan/"


def data_motor(**ubah):
    data = dict(no_polisi="KT 9 Z", tahun=2022, merk="Yamaha", model_kendaraan="NMAX",
                jenis_motor="Matic", kapasitas_mesin=155)
    data.update(ubah)
    return data


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rina", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.client.force_login(self.user)

    def motor(self, pelanggan=None, no="KT 1 A"):
        return Motor.objects.create(pelanggan=pelanggan or self.p, no_polisi=no, merk="Honda",
                                    model_kendaraan="Beat", tahun=2020, jenis_motor="Matic",
                                    kapasitas_mesin=110)


class KeadaanKosong(Dasar):
    def test_ajukan_dan_home_service_tanpa_form_dengan_tiga_langkah(self):
        for url in (AJUKAN, HOME):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertNotContains(r, 'name="keluhan"')
                self.assertContains(r, "Daftarkan kendaraan dulu")
                self.assertContains(r, 'class="langkah-mulai"')
                self.assertEqual(r.content.decode().count('class="lm-langkah'), 3)
                for jenis in ("mobil", "motor"):
                    self.assertContains(r, f"/pelanggan/kendaraan/tambah/{jenis}/?next={quote(url, safe='')}")
                self.assertContains(r, "Tambah Mobil")
                self.assertContains(r, "Tambah Motor")
                self.assertContains(r, "https://wa.me/")

    def test_punya_kendaraan_melihat_form_biasa(self):
        self.motor()
        for url in (AJUKAN, HOME):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertContains(r, 'name="keluhan"')
                self.assertNotContains(r, "Daftarkan kendaraan dulu")

    def test_garasi_kosong_menyebut_langkah_berikutnya(self):
        r = self.client.get(GARASI)
        self.assertContains(r, "Setelah kendaraan terdaftar, Anda bisa mengajukan servis atau memesan home service.")


class KembaliKeFormAsal(Dasar):
    def test_next_aman_dialihkan_ke_form_dengan_kendaraan_baru(self):
        for url in (AJUKAN, HOME):
            with self.subTest(url=url):
                no = "KT 7 A" if url == AJUKAN else "KT 8 B"
                r = self.client.post(f"/pelanggan/kendaraan/tambah/motor/?next={quote(url)}", data_motor(no_polisi=no))
                baru = Motor.objects.get(no_polisi=no)
                self.assertRedirects(r, f"{url}?kendaraan={baru.pk}", fetch_redirect_response=False)
                pesan = [str(m) for m in get_messages(r.wsgi_request)]
                self.assertIn("Kendaraan ditambahkan. Lanjutkan pengajuan servis Anda.", pesan)

    def test_next_ke_situs_luar_diabaikan(self):
        r = self.client.post("/pelanggan/kendaraan/tambah/motor/?next=https://jahat.example/", data_motor())
        self.assertRedirects(r, GARASI, fetch_redirect_response=False)

    def test_form_tambah_membawa_next(self):
        r = self.client.get(f"/pelanggan/kendaraan/tambah/mobil/?next={quote(AJUKAN)}")
        self.assertContains(r, f'action="/pelanggan/kendaraan/tambah/mobil/?next={quote(AJUKAN, safe="")}"')

    def test_kendaraan_awal_terpilih_hanya_milik_sendiri(self):
        milik = self.motor()
        lain = self.motor(Pelanggan.objects.create(user=User.objects.create_user(
            username="lain", password="x", role=User.ROLE_PELANGGAN)), no="KT 2 B")
        for url in (AJUKAN, HOME):
            with self.subTest(url=url):
                r = self.client.get(url, {"kendaraan": milik.pk})
                self.assertContains(r, f'value="motor:{milik.pk}" selected')
                r = self.client.get(url, {"kendaraan": lain.pk})
                self.assertNotContains(r, f'motor:{lain.pk}')
                self.assertNotContains(r, "selected>Motor")


class Beranda(Dasar):
    JUDUL = "Tambahkan kendaraan untuk mulai servis"

    def test_kotak_tampil_tanpa_kendaraan_dan_di_atas_profil(self):
        isi = self.client.get(BERANDA).content.decode()
        self.assertIn(self.JUDUL, isi)
        self.assertIn(f"/pelanggan/kendaraan/tambah/pilih/?next={quote(BERANDA, safe='')}", isi)
        self.assertLess(isi.index(self.JUDUL), isi.index("Profil Anda belum lengkap"))
        self.assertIn('class="aksi aksi-utama"', isi)

    def test_kotak_tidak_tampil_bila_punya_kendaraan(self):
        self.motor()
        r = self.client.get(BERANDA)
        self.assertNotContains(r, self.JUDUL)
        self.assertNotContains(r, "aksi-utama")

    def test_pilih_jenis_meneruskan_next(self):
        r = self.client.get(f"/pelanggan/kendaraan/tambah/pilih/?next={quote(BERANDA)}")
        self.assertContains(r, f"/pelanggan/kendaraan/tambah/motor/?next={quote(BERANDA, safe='')}")
