"""Halaman Garasi Saya, pilih jenis, dan form kendaraan (desain Figma).

Juga form kendaraan: no polisi dirapikan dan tidak boleh kembar meski beda
huruf besar/kecil, tahun dibatasi masuk akal, dan Batal kembali ke Garasi.
"""
from django.test import TestCase
from django.utils import timezone

from accounts.models import Pelanggan, User
from kendaraan.models import Kendaraan, Mobil, Motor
from pelanggan.forms import MobilForm, MotorForm
from servis.models import TransaksiServis as T

GARASI = "/pelanggan/kendaraan/"
PILIH = "/pelanggan/kendaraan/tambah/pilih/"


def data_motor(**ubah):
    data = dict(no_polisi="KT 5 E", tahun=2022, merk="Yamaha", model_kendaraan="NMAX",
                jenis_motor="Matic", kapasitas_mesin=155)
    data.update(ubah)
    return data


class Dasar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(username="k", password="x", role=User.ROLE_KASIR)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Honda", model_kendaraan="Beat",
            tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)
        self.client.force_login(self.user)


class FormKendaraan(Dasar):
    def test_no_polisi_dirapikan(self):
        form = MotorForm(data=data_motor(no_polisi="  kt   77  xy "))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["no_polisi"], "KT 77 XY")

    def test_no_polisi_kembar_beda_huruf_ditolak(self):
        form = MotorForm(data=data_motor(no_polisi="kt 1 a"))
        self.assertFalse(form.is_valid())
        self.assertIn("sudah terdaftar", form.errors["no_polisi"][0])

    def test_edit_tanpa_ganti_nomor_tidak_dianggap_kembar(self):
        form = MotorForm(data=data_motor(no_polisi="KT 1 A"), instance=self.motor)
        self.assertTrue(form.is_valid(), form.errors)

    def test_batas_tahun(self):
        tahun_depan = timezone.localdate().year + 1
        self.assertTrue(MotorForm(data=data_motor(tahun=tahun_depan)).is_valid())
        self.assertTrue(MotorForm(data=data_motor(tahun=1950)).is_valid())
        self.assertFalse(MotorForm(data=data_motor(tahun=tahun_depan + 1)).is_valid())
        self.assertFalse(MotorForm(data=data_motor(tahun=1949)).is_valid())

    def test_urutan_kolom_mengikuti_desain(self):
        self.assertEqual(list(MotorForm().fields),
                         ["no_polisi", "tahun", "merk", "model_kendaraan", "jenis_motor", "kapasitas_mesin"])
        self.assertEqual(list(MobilForm().fields),
                         ["no_polisi", "tahun", "merk", "model_kendaraan", "jenis_mobil", "jumlah_pintu"])


class Garasi(Dasar):
    def test_kartu_menampilkan_data_polimorfis(self):
        r = self.client.get(GARASI)
        self.assertContains(r, "Garasi Saya")
        self.assertContains(r, "Manajemen Kendaraan")
        self.assertContains(r, "Honda Beat")
        self.assertContains(r, "Matic, 110 cc")
        self.assertContains(r, 'href="#i-motor"')
        self.assertContains(r, "Belum pernah diservis")

    def test_kendaraan_dengan_riwayat_dikunci(self):
        T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=self.motor,
               keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        r = self.client.get(GARASI)
        self.assertContains(r, "1 kali servis")
        self.assertContains(r, 'href="#i-kunci"')
        # Gembok saja tidak jelas maksudnya; harus ada label dan alasannya.
        self.assertContains(r, "Tidak bisa dihapus")
        self.assertContains(r, "sudah punya riwayat servis")
        self.assertNotContains(r, f"/pelanggan/kendaraan/hapus/{self.motor.pk}/")

    def test_hanya_kendaraan_sendiri(self):
        lain = Pelanggan.objects.create(user=User.objects.create_user(
            username="lain", password="x", role=User.ROLE_PELANGGAN))
        Mobil.objects.create(pelanggan=lain, no_polisi="KT 9 Z", merk="Suzuki",
                             model_kendaraan="Ertiga", tahun=2018, jenis_mobil="MPV", jumlah_pintu=5)
        self.assertNotContains(self.client.get(GARASI), "KT 9 Z")

    def test_jumlah_query_tidak_bertambah_per_kendaraan(self):
        self.client.get(GARASI)  # pemanasan (sesi, context processor)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as satu:
            self.client.get(GARASI)
        for i in range(4):
            Mobil.objects.create(pelanggan=self.p, no_polisi=f"KT {i} M", merk="Toyota",
                                 model_kendaraan="Rush", tahun=2018, jenis_mobil="SUV", jumlah_pintu=5)
        with CaptureQueriesContext(connection) as lima:
            self.client.get(GARASI)
        self.assertEqual(len(satu), len(lima))

    def test_garasi_kosong(self):
        self.motor.delete()
        r = self.client.get(GARASI)
        self.assertContains(r, "Garasi Anda masih kosong")
        self.assertNotContains(r, 'class="garasi-daftar')


class TambahDanUbah(Dasar):
    def test_pilih_jenis_hanya_mobil_dan_motor(self):
        r = self.client.get(PILIH)
        self.assertContains(r, "/pelanggan/kendaraan/tambah/mobil/")
        self.assertContains(r, "/pelanggan/kendaraan/tambah/motor/")
        self.assertNotContains(r, "truk")

    def test_jenis_tak_dikenal_kembali_ke_pilihan(self):
        r = self.client.get("/pelanggan/kendaraan/tambah/truk/")
        self.assertRedirects(r, PILIH)

    def test_form_tambah_batal_dan_tutup_ke_garasi(self):
        r = self.client.get("/pelanggan/kendaraan/tambah/motor/")
        self.assertContains(r, "Langkah 2 dari 2")
        self.assertContains(r, "Simpan Kendaraan")
        self.assertContains(r, f'href="{GARASI}" class="tombol-teks">Batal')
        self.assertContains(r, "Dalam cc.")
        self.assertNotContains(r, "/pelanggan/dashboard/\" class=\"tombol-teks")

    def test_tambah_motor_kembali_ke_garasi(self):
        r = self.client.post("/pelanggan/kendaraan/tambah/motor/", data_motor(no_polisi="kt 5 e"), follow=True)
        self.assertRedirects(r, GARASI)
        self.assertContains(r, "Motor KT 5 E ditambahkan ke garasi.")
        baru = Motor.objects.get(no_polisi="KT 5 E")
        self.assertEqual(baru.pelanggan, self.p)

    def test_form_edit(self):
        url = f"/pelanggan/kendaraan/edit/{self.motor.pk}/"
        r = self.client.get(url)
        self.assertContains(r, "Simpan Perubahan")
        self.assertNotContains(r, "Langkah 2 dari 2")
        self.assertContains(r, 'value="KT 1 A"')

        r = self.client.post(url, data_motor(no_polisi="KT 1 A", kapasitas_mesin=125))
        self.assertRedirects(r, GARASI)
        self.motor.refresh_from_db()
        self.assertEqual(self.motor.kapasitas_mesin, 125)

    def test_edit_kendaraan_orang_lain_404(self):
        lain = Pelanggan.objects.create(user=User.objects.create_user(
            username="lain", password="x", role=User.ROLE_PELANGGAN))
        mobil = Mobil.objects.create(pelanggan=lain, no_polisi="KT 9 Z", merk="Suzuki",
                                     model_kendaraan="Ertiga", tahun=2018, jenis_mobil="MPV", jumlah_pintu=5)
        self.assertEqual(self.client.get(f"/pelanggan/kendaraan/edit/{mobil.pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"/pelanggan/kendaraan/hapus/{mobil.pk}/").status_code, 404)
        self.assertTrue(Kendaraan.objects.filter(pk=mobil.pk).exists())
