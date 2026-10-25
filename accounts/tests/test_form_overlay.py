"""Form tambah/ubah admin dibuka sebagai overlay, meniru form kendaraan pelanggan.

Tautan bertanda data-modal dimuat static/js/modal.js dengan header X-Modal.
Context processor accounts.context_processors.kerangka lalu memilih
_kerangka_modal.html (hanya isi kartu form) alih-alih kerangka.html, jadi
view tidak perlu tahu apa-apa soal overlay. Tanpa JavaScript, URL yang sama
tetap tampil sebagai halaman penuh dengan tombol Kembali di kiri atas.
"""
import io

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

FORM_TAMBAH = (
    "kelola_kasir_tambah", "kelola_pelanggan_tambah", "kelola_faq_tambah",
    "kelola_mekanik_tambah", "kelola_jenis_tambah", "pembelian:supplier_tambah",
    "sparepart:sparepart_create",
)


class FormAdminSebagaiOverlay(TestCase):
    def setUp(self):
        call_command("seed_demo", verbosity=0, stdout=io.StringIO(), izinkan_di_server=True)
        self.client.force_login(User.objects.get(username="admin1"))

    def test_dengan_header_x_modal_hanya_kartu_form(self):
        for nama in FORM_TAMBAH:
            with self.subTest(form=nama):
                respons = self.client.get(reverse(nama), HTTP_X_MODAL="1")
                self.assertEqual(respons.status_code, 200)
                self.assertContains(respons, 'class="kartu-modal"')
                self.assertContains(respons, "data-tutup-modal")
                self.assertNotContains(respons, "app-sidebar")

    def test_tanpa_javascript_halaman_penuh_dengan_tombol_kembali(self):
        for nama in FORM_TAMBAH:
            with self.subTest(form=nama):
                respons = self.client.get(reverse(nama))
                self.assertContains(respons, "app-sidebar")
                self.assertContains(respons, 'class="kartu-modal"')
                self.assertContains(respons, 'class="tautan-kembali"')

    def test_galat_validasi_tetap_di_overlay(self):
        respons = self.client.post(reverse("kelola_jenis_tambah"), {"nama_servis": ""}, HTTP_X_MODAL="1")
        self.assertEqual(respons.status_code, 200)
        self.assertContains(respons, "isian-galat")
        self.assertNotContains(respons, "app-sidebar")

    def test_tombol_tambah_dan_ikon_ubah_membuka_overlay(self):
        for daftar in ("kelola_kasir", "kelola_pelanggan", "kelola_faq", "kelola_mekanik",
                       "kelola_jenis", "pembelian:supplier_list", "sparepart:sparepart_list"):
            with self.subTest(halaman=daftar):
                isi = self.client.get(reverse(daftar)).content.decode()
                self.assertIn("js/modal.js", isi)
                self.assertRegex(isi, r'class="tombol-ikon" data-modal')
                self.assertRegex(isi, r'<a [^>]*data-modal[^>]*>\s*\+ Tambah')
