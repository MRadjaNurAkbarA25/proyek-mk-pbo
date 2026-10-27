"""Pengingat servis berkala: aturan di model Kendaraan (polimorfisme interval)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Pelanggan
from kendaraan.models import Kendaraan, Mobil, Motor
from servis.models import PengajuanServis, TransaksiServis as T


def buat_pelanggan(username="pel"):
    User = get_user_model()
    return Pelanggan.objects.create(user=User.objects.create_user(
        username=username, password="x", role=User.ROLE_PELANGGAN))


def buat_motor(pelanggan, plat="KT 1 MM"):
    return Motor.objects.create(pelanggan=pelanggan, no_polisi=plat, merk="Honda", model_kendaraan="Beat",
                                tahun=2021, jenis_motor="Matic", kapasitas_mesin=110)


def buat_mobil(pelanggan, plat="KT 2 MB"):
    return Mobil.objects.create(pelanggan=pelanggan, no_polisi=plat, merk="Toyota", model_kendaraan="Avanza",
                                tahun=2020, jumlah_pintu=4, jenis_mobil="MPV")


def servis(kendaraan, status, hari_lalu):
    """Transaksi berstatus `status` bertanggal `hari_lalu` hari yang lalu."""
    t = T.objects.create(pelanggan=kendaraan.pelanggan, kendaraan=kendaraan, status=status,
                         total_biaya=Decimal("100000"))
    T.objects.filter(pk=t.pk).update(tanggal=timezone.now() - timedelta(days=hari_lalu))
    return t


class Interval(TestCase):
    def test_mobil_dan_motor_punya_interval_sendiri(self):
        self.assertNotEqual(Mobil.INTERVAL_SERVIS_BERKALA_HARI, Motor.INTERVAL_SERVIS_BERKALA_HARI)
        self.assertTrue(Kendaraan.INTERVAL_SERVIS_BERKALA_HARI > 0)

    def test_jatuh_tempo_memakai_interval_subkelas(self):
        p = buat_pelanggan()
        motor, mobil = buat_motor(p), buat_mobil(p)
        servis(motor, T.STATUS_SELESAI, 10)
        servis(mobil, T.STATUS_SELESAI, 10)
        for k in (motor, mobil):
            with self.subTest(k=k.get_tipe()):
                self.assertEqual(k.jatuh_tempo_servis(),
                                 k.servis_terakhir() + timedelta(days=type(k).INTERVAL_SERVIS_BERKALA_HARI))
        self.assertNotEqual(motor.jatuh_tempo_servis(), mobil.jatuh_tempo_servis())

    def test_objek_induk_tetap_memakai_interval_subkelas(self):
        motor = buat_motor(buat_pelanggan())
        servis(motor, T.STATUS_SELESAI, 10)
        induk = Kendaraan.objects.get(pk=motor.pk)
        self.assertEqual(induk.jatuh_tempo_servis(), motor.jatuh_tempo_servis())


class ServisTerakhir(TestCase):
    def setUp(self):
        self.motor = buat_motor(buat_pelanggan())

    def test_belum_pernah_servis(self):
        self.assertIsNone(self.motor.servis_terakhir())
        self.assertIsNone(self.motor.jatuh_tempo_servis())
        self.assertFalse(self.motor.perlu_servis_berkala)

    def test_dihitung_dari_selesai_terakhir_bukan_yang_dibatalkan(self):
        selesai = servis(self.motor, T.STATUS_SELESAI, 100)
        servis(self.motor, T.STATUS_DIBATALKAN, 5)
        selesai.refresh_from_db()
        self.assertEqual(self.motor.servis_terakhir(), timezone.localtime(selesai.tanggal).date())

    def test_hanya_dibatalkan_dianggap_belum_pernah_servis(self):
        servis(self.motor, T.STATUS_DIBATALKAN, 100)
        self.assertIsNone(self.motor.servis_terakhir())

    def test_annotasi_dipakai_tanpa_query_tambahan(self):
        servis(self.motor, T.STATUS_SELESAI, 10)
        k = Kendaraan.dengan_servis_terakhir(
            Kendaraan.objects.select_related(*Kendaraan.relasi_subkelas())).get(pk=self.motor.pk)
        harapan = self.motor.jatuh_tempo_servis()
        with self.assertNumQueries(0):
            self.assertEqual(k.jatuh_tempo_servis(), harapan)


class PerluServisBerkala(TestCase):
    def setUp(self):
        self.motor = buat_motor(buat_pelanggan())
        lewat = Motor.INTERVAL_SERVIS_BERKALA_HARI + 5
        servis(self.motor, T.STATUS_SELESAI, lewat)

    def test_lewat_jatuh_tempo_diingatkan(self):
        self.assertTrue(self.motor.perlu_servis_berkala)

    def test_belum_jatuh_tempo_tidak_diingatkan(self):
        motor = buat_motor(self.motor.pelanggan, "KT 3 MM")
        servis(motor, T.STATUS_SELESAI, 3)
        self.assertFalse(motor.perlu_servis_berkala)

    def test_sedang_diservis_tidak_diingatkan(self):
        servis(self.motor, T.STATUS_DIKERJAKAN, 0)
        self.assertFalse(self.motor.perlu_servis_berkala)

    def test_punya_pengajuan_menunggu_tidak_diingatkan(self):
        PengajuanServis.objects.create(pelanggan=self.motor.pelanggan, kendaraan=self.motor, keluhan="rutin")
        self.assertFalse(self.motor.perlu_servis_berkala)
