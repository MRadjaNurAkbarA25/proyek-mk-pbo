"""Kartu Garasi Saya di beranda (QoL A2).

Paling banyak 3 kendaraan, diurutkan dari yang paling baru diservis;
tautan kecil "Lihat semua (n)" hanya muncul kalau kendaraannya lebih dari 3.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Pelanggan, User
from kendaraan.models import Mobil, Motor
from servis.models import TransaksiServis as T


class GarasiBeranda(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="x", role=User.ROLE_PELANGGAN)
        self.p = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(username="k", password="x", role=User.ROLE_KASIR)
        self.client.force_login(self.user)

    def motor(self, plat):
        return Motor.objects.create(pelanggan=self.p, no_polisi=plat, merk="Honda", model_kendaraan=f"M{plat}",
                                    tahun=2020, jenis_motor="Matic", kapasitas_mesin=110)

    def servis(self, kendaraan, hari_lalu):
        t = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=kendaraan,
                   keluhan="k", tipe_layanan=T.TIPE_DI_BENGKEL)
        T.objects.filter(pk=t.pk).update(status=T.STATUS_SELESAI,
                                         tanggal=timezone.now() - timedelta(days=hari_lalu))

    def garasi(self):
        return [g["plat"] for g in self.client.get("/pelanggan/dashboard/").context["garasi"]]

    def test_urut_dari_servis_terbaru_maks_tiga(self):
        a, b, c, d = (self.motor(f"KT {i} A") for i in range(1, 5))
        Mobil.objects.create(pelanggan=self.p, no_polisi="KT 5 A", merk="Toyota", model_kendaraan="Rush",
                             tahun=2018, jenis_mobil="SUV", jumlah_pintu=5)
        self.servis(a, 30)
        self.servis(c, 2)
        self.servis(b, 10)
        # c (2 hari) > b (10 hari) > a (30 hari); d dan mobil belum pernah diservis.
        self.assertEqual(self.garasi(), ["KT 3 A", "KT 2 A", "KT 1 A"])

        r = self.client.get("/pelanggan/dashboard/")
        self.assertContains(r, "Lihat semua (5)")

    def test_yang_belum_diservis_diurutkan_terbaru_didaftarkan(self):
        self.motor("KT 1 A")
        self.motor("KT 2 A")
        self.assertEqual(self.garasi(), ["KT 2 A", "KT 1 A"])

    def test_tiga_atau_kurang_tanpa_tautan(self):
        for i in range(3):
            self.motor(f"KT {i} B")
        self.assertNotContains(self.client.get("/pelanggan/dashboard/"), "Lihat semua (")

    def test_ikon_sesuai_jenis(self):
        self.motor("KT 1 A")
        self.assertContains(self.client.get("/pelanggan/dashboard/"), 'href="#i-motor"')
