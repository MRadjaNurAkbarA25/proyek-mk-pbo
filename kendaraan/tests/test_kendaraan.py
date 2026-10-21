"""Uji model Kendaraan: polimorfisme Mobil/Motor dan aturan hapus.

Yang dijaga di sini:
- method yang di-override subkelas (get_tipe, deskripsi_khusus, ikon);
- spesifik(): baris Kendaraan induk kembali menjadi Mobil/Motor, supaya
  template dan view tidak perlu percabangan "kalau mobil ... kalau motor";
- SUBKELAS sebagai satu-satunya daftar jenis kendaraan (Truk sudah dihapus);
- kendaraan dengan pengajuan servis yang menunggu kasir tidak bisa dihapus.
"""
from django.test import TestCase

from accounts.models import Pelanggan, User
from kendaraan.models import Kendaraan, Mobil, Motor
from servis.models import PengajuanServis


def buat_pelanggan(username="budi"):
    user = User.objects.create_user(username=username, password="x", role=User.ROLE_PELANGGAN)
    return Pelanggan.objects.create(user=user)


class DasarKendaraan(TestCase):
    def setUp(self):
        self.p = buat_pelanggan()
        self.mobil = Mobil.objects.create(
            pelanggan=self.p, no_polisi="KT 1 A", merk="Toyota", model_kendaraan="Avanza",
            tahun=2019, jenis_mobil="MPV", jumlah_pintu=5)
        self.motor = Motor.objects.create(
            pelanggan=self.p, no_polisi="KT 2 B", merk="Honda", model_kendaraan="Beat",
            tahun=2021, jenis_motor="Matic", kapasitas_mesin=110)


class Polimorfisme(DasarKendaraan):
    def test_method_yang_dioverride(self):
        self.assertEqual(self.mobil.get_tipe(), "Mobil")
        self.assertEqual(self.motor.get_tipe(), "Motor")
        self.assertEqual(self.mobil.deskripsi_khusus(), "MPV, 5 pintu")
        self.assertEqual(self.motor.deskripsi_khusus(), "Matic, 110 cc")
        self.assertEqual(self.mobil.ikon, "mobil")
        self.assertEqual(self.motor.ikon, "motor")

    def test_spesifik_mengembalikan_subkelas_dari_baris_induk(self):
        induk_mobil = Kendaraan.objects.get(pk=self.mobil.pk)
        induk_motor = Kendaraan.objects.get(pk=self.motor.pk)
        self.assertIs(type(induk_mobil), Kendaraan)

        self.assertIsInstance(induk_mobil.spesifik(), Mobil)
        self.assertIsInstance(induk_motor.spesifik(), Motor)
        self.assertEqual(induk_motor.spesifik().ikon, "motor")
        self.assertEqual(induk_motor.spesifik().deskripsi_khusus(), "Matic, 110 cc")

    def test_spesifik_pada_subkelas_mengembalikan_dirinya(self):
        self.assertIs(self.motor.spesifik(), self.motor)

    def test_spesifik_tanpa_query_tambahan_bila_select_related(self):
        daftar = list(Kendaraan.objects.select_related(*Kendaraan.relasi_subkelas()))
        with self.assertNumQueries(0):
            jenis = sorted(k.spesifik().get_tipe() for k in daftar)
        self.assertEqual(jenis, ["Mobil", "Motor"])

    def test_baris_induk_tanpa_subkelas_tidak_error(self):
        """Data rusak (induk tanpa baris Mobil/Motor) tetap bisa ditampilkan."""
        yatim = Kendaraan.objects.create(
            pelanggan=self.p, no_polisi="KT 9 Z", merk="X", model_kendaraan="Y", tahun=2000)
        self.assertIs(yatim.spesifik(), yatim)
        self.assertEqual(yatim.ikon, "mobil")


class DaftarSubkelas(TestCase):
    def test_hanya_mobil_dan_motor(self):
        self.assertEqual(Kendaraan.model_subkelas(), (Mobil, Motor))
        self.assertEqual(Kendaraan.relasi_subkelas(), ("mobil", "motor"))
        self.assertEqual(Kendaraan.relasi_subkelas("kendaraan__"),
                         ("kendaraan__mobil", "kendaraan__motor"))

    def test_truk_sudah_tidak_ada(self):
        import kendaraan.models as m
        self.assertFalse(hasattr(m, "Truk"))


class HapusSaatPengajuanMenunggu(DasarKendaraan):
    """PengajuanServis.kendaraan memakai CASCADE. Dulu menghapus kendaraan
    ikut menghapus pengajuan yang sedang ditunggu kasir tanpa jejak."""

    def ajukan(self, status=PengajuanServis.STATUS_MENUNGGU):
        return PengajuanServis.objects.create(
            pelanggan=self.p, kendaraan=self.motor, keluhan="Rem bunyi", status=status)

    def test_pengajuan_menunggu_menahan_hapus(self):
        self.ajukan()
        self.assertIn("pengajuan servis", self.motor.alasan_tidak_bisa_dihapus())
        self.assertFalse(self.motor.bisa_dihapus)

    def test_pengajuan_yang_sudah_selesai_tidak_menahan(self):
        self.ajukan(PengajuanServis.STATUS_DITOLAK)
        self.ajukan(PengajuanServis.STATUS_DIBATALKAN)
        self.assertIsNone(self.motor.alasan_tidak_bisa_dihapus())

    def test_teks_status_sama_dengan_konstanta_pengajuan(self):
        """kendaraan/models.py menulis "MENUNGGU" langsung; jaga agar tetap sama."""
        self.assertEqual(PengajuanServis.STATUS_MENUNGGU, "MENUNGGU")

    def test_halaman_hapus_menolak_dan_pengajuan_tetap_ada(self):
        pengajuan = self.ajukan()
        self.client.force_login(self.p.user)
        respons = self.client.post(f"/pelanggan/kendaraan/hapus/{self.motor.pk}/", follow=True)
        self.assertTrue(Kendaraan.objects.filter(pk=self.motor.pk).exists())
        self.assertTrue(PengajuanServis.objects.filter(pk=pengajuan.pk).exists())
        self.assertContains(respons, "menunggu persetujuan kasir")
