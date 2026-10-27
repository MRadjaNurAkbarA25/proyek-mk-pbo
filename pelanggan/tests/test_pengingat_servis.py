"""Pengingat servis berkala di beranda, Garasi Saya, dan form Ajukan Servis."""
from django.test import TestCase
from django.urls import reverse

from kendaraan.models import Motor
from kendaraan.tests.test_servis_berkala import buat_mobil, buat_motor, buat_pelanggan, servis
from servis.models import TransaksiServis as T

LEWAT = Motor.INTERVAL_SERVIS_BERKALA_HARI + 5


class DasarPengingat(TestCase):
    def setUp(self):
        self.pelanggan = buat_pelanggan()
        self.motor = buat_motor(self.pelanggan)
        self.client.force_login(self.pelanggan.user)


class KartuBeranda(DasarPengingat):
    def test_kartu_muncul_dengan_tombol_ajukan(self):
        servis(self.motor, T.STATUS_SELESAI, LEWAT)
        isi = self.client.get(reverse("pelanggan_dashboard")).content.decode()
        self.assertIn("Saatnya servis berkala", isi)
        self.assertIn(f'{reverse("ajukan_servis")}?kendaraan={self.motor.pk}', isi)
        self.assertIn(self.motor.no_polisi, isi.split("Saatnya servis berkala", 1)[1])

    def test_tanpa_kendaraan_jatuh_tempo_kartu_tidak_muncul(self):
        servis(self.motor, T.STATUS_SELESAI, 3)
        self.assertNotContains(self.client.get(reverse("pelanggan_dashboard")), "Saatnya servis berkala")

    def test_kendaraan_yang_belum_pernah_servis_tidak_diingatkan(self):
        self.assertNotContains(self.client.get(reverse("pelanggan_dashboard")), "Saatnya servis berkala")

    def test_hanya_kendaraan_yang_jatuh_tempo_yang_tercantum(self):
        servis(self.motor, T.STATUS_SELESAI, LEWAT)
        mobil = buat_mobil(self.pelanggan)
        servis(mobil, T.STATUS_SELESAI, 3)
        kartu = self.client.get(reverse("pelanggan_dashboard")).context["servis_berkala"]
        self.assertEqual([k["plat"] for k in kartu], [self.motor.no_polisi])


class FormAjukanTerisi(DasarPengingat):
    def test_kendaraan_dari_tautan_terpilih(self):
        respons = self.client.get(reverse("ajukan_servis"), {"kendaraan": self.motor.pk})
        self.assertEqual(respons.context["form"]["kendaraan"].value(), f"motor:{self.motor.pk}")
        self.assertContains(respons, f'value="motor:{self.motor.pk}" selected')

    def test_kendaraan_milik_orang_lain_tidak_bisa_dipakai(self):
        lain = buat_motor(buat_pelanggan("lain"), "KT 9 ZZ")
        respons = self.client.get(reverse("ajukan_servis"), {"kendaraan": lain.pk})
        self.assertFalse(respons.context["form"]["kendaraan"].value())
        self.assertNotContains(respons, "KT 9 ZZ")

    def test_nilai_ngawur_diabaikan(self):
        respons = self.client.get(reverse("ajukan_servis"), {"kendaraan": "abc"})
        self.assertEqual(respons.status_code, 200)
        self.assertFalse(respons.context["form"]["kendaraan"].value())


class GarasiSaya(DasarPengingat):
    def _kartu(self):
        return self.client.get(reverse("kendaraan_saya")).content.decode()

    def test_sudah_waktunya_servis(self):
        servis(self.motor, T.STATUS_SELESAI, LEWAT)
        self.assertIn("Sudah waktunya servis", self._kartu())

    def test_servis_berikutnya_bila_belum_jatuh_tempo(self):
        servis(self.motor, T.STATUS_SELESAI, 3)
        isi = self._kartu()
        self.assertIn("Servis berikutnya:", isi)
        self.assertNotIn("Sudah waktunya servis", isi)

    def test_belum_pernah_servis_tanpa_pengingat(self):
        isi = self._kartu()
        self.assertNotIn("Servis berikutnya:", isi)
        self.assertNotIn("Sudah waktunya servis", isi)
