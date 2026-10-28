"""Atribut `tahun` kendaraan adalah tahun pembuatan (seperti di STNK), bukan tahun beli/daftar."""
from django.test import TestCase
from django.utils import timezone

from accounts.models import Pelanggan, User
from faq.data_awal import isi_faq_awal
from faq.models import PertanyaanFAQ
from kendaraan.models import Kendaraan, Motor
from pelanggan.forms import MobilForm, MotorForm


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda", model_kendaraan="Beat",
            tahun=2018, jenis_motor="Matic", kapasitas_mesin=110)


class ModelDanForm(TestCase):
    def test_verbose_name_model(self):
        self.assertEqual(Kendaraan._meta.get_field("tahun").verbose_name, "Tahun pembuatan")

    def test_label_placeholder_dan_bantuan_form(self):
        for Form in (MobilForm, MotorForm):
            with self.subTest(form=Form.__name__):
                f = Form()["tahun"]
                self.assertEqual(f.label, "Tahun Pembuatan")
                self.assertEqual(f.field.widget.attrs["placeholder"], "Contoh: 2020")
                self.assertEqual(f.help_text, "Lihat STNK kendaraan")

    def test_pesan_galat(self):
        batas = timezone.localdate().year + 1
        form = MotorForm(data={"tahun": 1900})
        form.is_valid()
        self.assertEqual(form.errors["tahun"], [f"Tahun pembuatan harus antara 1950 dan {batas}."])


class Tampilan(Dasar):
    def test_garasi_saya(self):
        self.client.force_login(self.user)
        r = self.client.get("/pelanggan/kendaraan/")
        self.assertContains(r, "<dt>Tahun Pembuatan</dt>", html=False)
        self.assertNotContains(r, "<dt>Tahun</dt>")

    def test_data_kendaraan_admin(self):
        admin = User.objects.create_user(username="adm", password="x", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        r = self.client.get("/adminpanel/kendaraan/")
        self.assertContains(r, "th. pembuatan 2018")

    def test_cari_kendaraan_kasir(self):
        kasir = User.objects.create_user(username="ksr", password="x", role=User.ROLE_KASIR)
        self.client.force_login(kasir)
        r = self.client.get("/kasir/kendaraan/cari/", {"q": "KT 1"})
        self.assertContains(r, "th. pembuatan 2018")
        self.assertNotContains(r, "(2018)")


class FaqTahunPembuatan(TestCase):
    def test_faq_menyebut_tahun_pembuatan(self):
        isi_faq_awal()
        for q in ("Bagaimana cara mendaftarkan kendaraan saya?", "Bagaimana cara mengubah data kendaraan?"):
            with self.subTest(q=q):
                self.assertIn("tahun pembuatan", PertanyaanFAQ.objects.get(pertanyaan=q).jawaban)

    def test_faq_lama_di_database_ikut_diperbarui(self):
        PertanyaanFAQ.objects.create(
            kategori=PertanyaanFAQ.KATEGORI_CHOICES[0][0],
            pertanyaan="Bagaimana cara mengubah data kendaraan?",
            jawaban="Buka menu Kendaraan Saya, pilih kendaraannya, lalu klik ubah. Data seperti nomor polisi, "
                    "merek, model, dan tahun bisa diperbaiki di sana.",
            kata_kunci="ubah")
        isi_faq_awal()
        self.assertIn("tahun pembuatan",
                      PertanyaanFAQ.objects.get(pertanyaan="Bagaimana cara mengubah data kendaraan?").jawaban)
