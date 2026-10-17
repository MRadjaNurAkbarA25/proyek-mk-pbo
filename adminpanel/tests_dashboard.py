"""Uji kartu ringkasan dashboard admin.

Angka pada kartu dihitung dengan agregasi, jadi yang diuji adalah apakah
hitungannya benar, bukan sekadar halamannya terbuka.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from pembayaran.models import Pembayaran
from servis.models import TransaksiServis
from sparepart.models import Sparepart

SANDI = "rahasia12345"


class DashboardAdminTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm", password=SANDI, role=User.ROLE_ADMIN
        )
        user_pel = User.objects.create_user(
            username="pel", password=SANDI, role=User.ROLE_PELANGGAN
        )
        self.pelanggan = Pelanggan.objects.create(user=user_pel)
        self.client.login(username="adm", password=SANDI)

    def _motor(self, polisi):
        return Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi=polisi, merk="Honda",
            model_kendaraan="Beat", tahun=2021, jenis_motor="Matic",
            kapasitas_mesin=110,
        )

    def _konteks(self):
        return self.client.get(reverse("admin_dashboard")).context

    # ---------- hak akses ----------

    def test_hanya_admin_yang_boleh_membuka(self):
        User.objects.create_user(
            username="kas", password=SANDI, role=User.ROLE_KASIR
        )
        self.client.login(username="kas", password=SANDI)
        self.assertEqual(
            self.client.get(reverse("admin_dashboard")).status_code, 302
        )

    # ---------- kartu servis berjalan ----------

    def test_servis_berjalan_hanya_menghitung_status_aktif(self):
        TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self._motor("KT 1 AA"),
            keluhan="aktif", tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
        )
        selesai = TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self._motor("KT 2 BB"),
            keluhan="selesai", tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
        )
        selesai.status = TransaksiServis.STATUS_SELESAI
        selesai.save(update_fields=["status"])

        self.assertEqual(self._konteks()["transaksi_aktif"], 1)

    def test_dashboard_kosong_menampilkan_nol_bukan_error(self):
        konteks = self._konteks()
        self.assertEqual(konteks["transaksi_aktif"], 0)
        self.assertEqual(konteks["pendapatan_bulan"], 0)
        self.assertEqual(konteks["sparepart_kritis"], 0)
        self.assertEqual(konteks["mekanik_total"], 0)

    # ---------- kartu pendapatan ----------

    def test_pendapatan_hanya_menjumlah_bulan_ini(self):
        transaksi = TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self._motor("KT 3 CC"),
            keluhan="dibayar", tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
        )
        transaksi.status = TransaksiServis.STATUS_SELESAI
        transaksi.total_biaya = 200000
        transaksi.save(update_fields=["status", "total_biaya"])
        pembayaran = Pembayaran.buat(
            transaksi, Pembayaran.METODE_CASH, uang_dibayar=200000
        )

        konteks = self._konteks()
        self.assertEqual(konteks["pendapatan_bulan"], 200000)
        self.assertEqual(konteks["pembayaran_bulan"], 1)

        # Pembayaran bulan lalu tidak boleh ikut terhitung.
        bulan_lalu = timezone.now().replace(day=1) - timedelta(days=5)
        Pembayaran.objects.filter(pk=pembayaran.pk).update(tanggal=bulan_lalu)

        konteks = self._konteks()
        self.assertEqual(konteks["pendapatan_bulan"], 0)
        self.assertEqual(konteks["pembayaran_bulan"], 0)

    # ---------- kartu stok ----------

    def test_stok_kritis_menghitung_yang_di_bawah_atau_sama_dengan_minimum(self):
        Sparepart.objects.create(kode="A1", nama="Aman", kategori="Oli",
                                 harga=1000, stok=10, stok_minimum=5)
        Sparepart.objects.create(kode="A2", nama="Pas Minimum", kategori="Oli",
                                 harga=1000, stok=5, stok_minimum=5)
        Sparepart.objects.create(kode="A3", nama="Kurang", kategori="Oli",
                                 harga=1000, stok=1, stok_minimum=5)

        konteks = self._konteks()
        self.assertEqual(konteks["sparepart_kritis"], 2)
        self.assertEqual(konteks["sparepart_total"], 3)

    # ---------- kartu mekanik ----------

    def test_mekanik_tersedia_dan_cuti_dihitung_terpisah(self):
        for i, status in enumerate([
            Mekanik.STATUS_TERSEDIA, Mekanik.STATUS_TERSEDIA, Mekanik.STATUS_CUTI
        ]):
            u = User.objects.create_user(
                username=f"mek{i}", password=SANDI, role=User.ROLE_MEKANIK
            )
            Mekanik.objects.create(user=u, status=status)

        konteks = self._konteks()
        self.assertEqual(konteks["mekanik_total"], 3)
        self.assertEqual(konteks["mekanik_tersedia"], 2)
        self.assertEqual(konteks["mekanik_cuti"], 1)

    # ---------- tampilan ----------

    def test_judul_kartu_tampil_di_halaman(self):
        isi = self.client.get(reverse("admin_dashboard")).content.decode()
        for judul in ("Servis Berjalan", "Pendapatan", "Stok Perlu Dibeli",
                      "Mekanik Siap Kerja", "Servis Terakhir Masuk"):
            self.assertIn(judul, isi)

    def test_servis_terbaru_dibatasi_lima_baris(self):
        for i in range(7):
            TransaksiServis.objects.create(
                pelanggan=self.pelanggan, kendaraan=self._motor(f"KT {50 + i} ZZ"),
                keluhan=f"uji {i}", tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
            )
        self.assertEqual(len(self._konteks()["servis_terbaru"]), 5)
