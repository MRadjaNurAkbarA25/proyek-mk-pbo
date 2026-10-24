"""Perbaikan tampilan pelanggan dari hasil konsultasi dosen.

- Beranda: kartu tersusun dua baris sejajar (Status | Aksi Cepat,
  Riwayat | Garasi), stepper status bergaris.
- Kendaraan Saya: tambah/edit dibuka sebagai overlay. View mengirim potongan
  isi (tanpa kerangka halaman) kalau request membawa header X-Modal; tanpa
  header itu URL lama tetap berupa halaman penuh.
- Ajukan Servis dan Home Service memakai teks besar (kelas hal-besar).
- Menu "Persetujuan Diagnosis" tidak dipotong menjadi dua baris.
"""
from django.test import TestCase

from accounts.models import Pelanggan, User
from kendaraan.models import Motor

GARASI = "/pelanggan/kendaraan/"
PILIH = "/pelanggan/kendaraan/tambah/pilih/"
MODAL = {"HTTP_X_MODAL": "1"}


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda", model_kendaraan="Beat",
            tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)
        self.client.force_login(self.user)


class ModalKendaraan(Dasar):
    def test_tombol_garasi_bertanda_modal(self):
        r = self.client.get(GARASI)
        self.assertContains(r, f'href="{PILIH}" class="btn-garis-tebal" data-modal')
        self.assertContains(r, f'href="/pelanggan/kendaraan/edit/{self.motor.pk}/" class="tombol-ikon" data-modal')
        self.assertContains(r, 'id="modal-kendaraan"')

    def test_pilih_jenis_sebagai_potongan(self):
        r = self.client.get(PILIH, **MODAL)
        self.assertTemplateUsed(r, "pelanggan/_pilih_tipe_isi.html")
        self.assertTemplateNotUsed(r, "pelanggan/base.html")
        self.assertContains(r, 'href="/pelanggan/kendaraan/tambah/motor/"')

    def test_form_tambah_sebagai_potongan(self):
        r = self.client.get("/pelanggan/kendaraan/tambah/motor/", **MODAL)
        self.assertTemplateUsed(r, "pelanggan/_form_kendaraan_isi.html")
        self.assertTemplateNotUsed(r, "pelanggan/base.html")
        self.assertContains(r, "Langkah 2 dari 2")

    def test_galat_tetap_di_potongan(self):
        r = self.client.post("/pelanggan/kendaraan/tambah/motor/",
                             {"no_polisi": "", "tahun": 2022}, **MODAL)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateNotUsed(r, "pelanggan/base.html")
        self.assertContains(r, "isian-galat")
        self.assertFalse(Motor.objects.filter(merk="").exists())

    def test_simpan_lewat_modal_tetap_redirect(self):
        r = self.client.post(f"/pelanggan/kendaraan/edit/{self.motor.pk}/", {
            "no_polisi": "KT 1 A", "tahun": 2020, "merk": "Honda", "model_kendaraan": "Beat",
            "jenis_motor": "Matic", "kapasitas_mesin": 125}, **MODAL)
        self.assertRedirects(r, GARASI)
        self.motor.refresh_from_db()
        self.assertEqual(self.motor.kapasitas_mesin, 125)

    def test_tanpa_header_tetap_halaman_penuh(self):
        for url in (PILIH, "/pelanggan/kendaraan/tambah/motor/", f"/pelanggan/kendaraan/edit/{self.motor.pk}/"):
            r = self.client.get(url)
            self.assertTemplateUsed(r, "pelanggan/base.html")


class TampilanBeranda(Dasar):
    def test_empat_kartu_dalam_satu_grid_berurutan(self):
        html = self.client.get("/pelanggan/dashboard/").content.decode()
        self.assertNotIn("kolom-samping", html)
        posisi = [html.index(t) for t in ("Status Servis Saat Ini", "Aksi Cepat", "Riwayat Terakhir", "Garasi Saya")]
        self.assertEqual(posisi, sorted(posisi))


class TampilanLain(Dasar):
    def test_form_servis_bertulisan_besar(self):
        for url in ("/pelanggan/ajukan-servis/", "/pelanggan/home-service/pesan/"):
            self.assertContains(self.client.get(url), 'class="hal-besar"')

    def test_menu_persetujuan_satu_baris(self):
        r = self.client.get("/pelanggan/dashboard/")
        self.assertContains(r, "Persetujuan Diagnosis")
        with open("static/css/pelanggan.css", encoding="utf-8") as f:
            css = f.read()
        self.assertIn("--sidebar: 290px", css)
        self.assertIn("white-space: nowrap", css.split(".menu a, .menu .menu-keluar {")[1].split("}")[0])
