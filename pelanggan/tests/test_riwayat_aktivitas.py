"""Riwayat pelanggan diurutkan menurut aktivitas terakhir, bukan tanggal dibuat.

Masalah dari demo: transaksi lama yang baru diproses hari ini tetap di bawah
dan tetap menampilkan tanggal dibuatnya. Field tanggal (waktu dibuat) tidak
diubah karena dipakai kode transaksi dan laporan; urutan memakai waktu
PembaruanServis terakhir, atau tanggal dibuat kalau belum ada pembaruan.
"""
from datetime import timedelta

from django.db import connection
from django.template.defaultfilters import date as format_tanggal
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import Pelanggan, User
from kendaraan.models import Motor
from servis.models import PembaruanServis, TransaksiServis

URL_RIWAYAT = "/pelanggan/riwayat/"


def tampil(waktu, pola):
    return format_tanggal(timezone.localtime(waktu), pola)


class DasarRiwayat(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi", password="demo12345", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=self.user)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1234 ZZ",
            merk="Honda", model_kendaraan="Beat", tahun=2020,
            jenis_motor="Matic", kapasitas_mesin=110)
        self.sekarang = timezone.now()
        # Dibuat 10 hari lalu, lalu 2 hari lalu; keduanya belum punya pembaruan.
        self.lama = self.transaksi(hari_lalu=10, keluhan="Rem bunyi")
        self.baru = self.transaksi(hari_lalu=2, keluhan="Ganti oli")
        self.client.force_login(self.user)

    def transaksi(self, hari_lalu, **data):
        t = TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor,
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL, **data)
        # tanggal memakai auto_now_add, jadi dimundurkan lewat update().
        TransaksiServis.objects.filter(pk=t.pk).update(
            tanggal=self.sekarang - timedelta(days=hari_lalu))
        t.refresh_from_db()
        return t

    def perbarui(self, transaksi, waktu):
        p = transaksi.catat(PembaruanServis.TAHAP_PERBAIKAN, "Sedang dikerjakan.")
        PembaruanServis.objects.filter(pk=p.pk).update(waktu=waktu)

    def urutan_riwayat(self, **params):
        r = self.client.get(URL_RIWAYAT, params)
        self.assertEqual(r.status_code, 200)
        return [t.pk for t in r.context["daftar"]]


class AktivitasTerakhir(DasarRiwayat):
    def test_tanpa_pembaruan_jatuh_ke_tanggal_dibuat(self):
        hasil = TransaksiServis.dengan_aktivitas_terakhir(
            TransaksiServis.objects.filter(pk=self.lama.pk)).get()
        self.assertEqual(hasil.terakhir_diperbarui, self.lama.tanggal)

    def test_memakai_pembaruan_paling_akhir(self):
        self.perbarui(self.lama, self.sekarang - timedelta(days=5))
        self.perbarui(self.lama, self.sekarang - timedelta(hours=1))
        hasil = TransaksiServis.dengan_aktivitas_terakhir(
            TransaksiServis.objects.filter(pk=self.lama.pk)).get()
        self.assertEqual(hasil.terakhir_diperbarui, self.sekarang - timedelta(hours=1))

    def test_tanggal_dibuat_tidak_berubah(self):
        self.perbarui(self.lama, self.sekarang)
        self.lama.refresh_from_db()
        self.assertEqual(self.lama.tanggal, self.sekarang - timedelta(days=10))


class HalamanRiwayat(DasarRiwayat):
    def test_tanpa_pembaruan_urut_tanggal_dibuat(self):
        self.assertEqual(self.urutan_riwayat(), [self.baru.pk, self.lama.pk])
        html = self.client.get(URL_RIWAYAT).content.decode()
        self.assertIn(f"Dibuat {tampil(self.lama.tanggal, 'd M Y')}", html)
        self.assertNotIn("Diperbarui", html)

    def test_transaksi_lama_yang_diproses_naik_ke_atas(self):
        waktu = self.sekarang - timedelta(minutes=5)
        self.perbarui(self.lama, waktu)
        self.assertEqual(self.urutan_riwayat(), [self.lama.pk, self.baru.pk])
        html = self.client.get(URL_RIWAYAT).content.decode()
        self.assertIn(f"Dibuat {tampil(self.lama.tanggal, 'd M Y')}", html)
        self.assertIn(f"Diperbarui {tampil(waktu, 'd M Y, H:i')}", html)

    def test_pembaruan_di_hari_yang_sama_tidak_diulang(self):
        self.perbarui(self.baru, self.baru.tanggal + timedelta(seconds=30))
        html = self.client.get(URL_RIWAYAT).content.decode()
        self.assertNotIn("Diperbarui", html)

    def test_filter_status_dan_pencarian_tetap_jalan(self):
        self.perbarui(self.lama, self.sekarang)
        TransaksiServis.objects.filter(pk=self.baru.pk).update(
            status=TransaksiServis.STATUS_SELESAI)
        self.assertEqual(
            self.urutan_riwayat(status=TransaksiServis.STATUS_SELESAI), [self.baru.pk])
        self.assertEqual(
            self.urutan_riwayat(q=self.lama.kode_transaksi), [self.lama.pk])
        self.assertEqual(self.urutan_riwayat(q="Beat"), [self.lama.pk, self.baru.pk])

    def test_paginasi_tetap_jalan(self):
        for i in range(25):
            self.transaksi(hari_lalu=20 + i)
        r = self.client.get(URL_RIWAYAT)
        halaman = r.context["halaman"]
        self.assertEqual(halaman.paginator.count, 27)
        self.assertTrue(halaman.has_next())
        kedua = self.client.get(URL_RIWAYAT, {"page": 2})
        self.assertEqual(kedua.status_code, 200)
        semua = [t.pk for t in r.context["daftar"]] + [t.pk for t in kedua.context["daftar"]]
        self.assertEqual(len(set(semua)), len(semua))

    def test_jumlah_query_tidak_bertambah_per_baris(self):
        with CaptureQueriesContext(connection) as dua:
            self.client.get(URL_RIWAYAT)
        for i in range(5):
            t = self.transaksi(hari_lalu=3 + i)
            self.perbarui(t, self.sekarang - timedelta(hours=i))
        with CaptureQueriesContext(connection) as tujuh:
            self.client.get(URL_RIWAYAT)
        self.assertEqual(len(tujuh), len(dua))


class DetailDanBeranda(DasarRiwayat):
    def test_detail_menampilkan_terakhir_diperbarui(self):
        waktu = self.sekarang - timedelta(minutes=5)
        self.perbarui(self.lama, waktu)
        r = self.client.get(f"/pelanggan/riwayat/{self.lama.pk}/")
        self.assertContains(r, f"Terakhir diperbarui {tampil(waktu, 'd M Y, H:i')}")

    def test_detail_tanpa_pembaruan_memakai_tanggal_dibuat(self):
        r = self.client.get(f"/pelanggan/riwayat/{self.baru.pk}/")
        self.assertContains(r, f"Terakhir diperbarui {tampil(self.baru.tanggal, 'd M Y, H:i')}")

    def test_riwayat_terakhir_di_beranda_ikut_aktivitas(self):
        from pelanggan.beranda import _tanggal, data_beranda

        waktu = self.sekarang - timedelta(minutes=5)
        self.perbarui(self.lama, waktu)
        riwayat = data_beranda(self.user, self.pelanggan)["riwayat"]
        # Transaksi lama yang baru diproses di atas, dengan tanggal pembaruannya.
        self.assertEqual([r["tanggal"] for r in riwayat],
                         [_tanggal(waktu), _tanggal(self.baru.tanggal)])
