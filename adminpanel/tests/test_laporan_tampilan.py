"""Uji tampilan kelima laporan admin dan beranda admin.

Yang diuji di sini hanya hal yang diminta penyamaan tampilan: nama yang
dipakai (nama tampil, bukan username login), tombol Cetak di kelima laporan,
dan tautan Laporan Pembelian di kartu "Laporan" pada beranda.

Angka laporan sengaja TIDAK diuji di sini — itu sudah punya tesnya sendiri di
adminpanel/tests/test_laporan_views.py, dan perhitungannya tidak boleh berubah.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Mekanik, Pelanggan
from kendaraan.models import Motor
from servis.models import TransaksiServis
from sparepart.models import Sparepart

SANDI = "rahasia12345"

LIMA_LAPORAN = (
    "laporan_transaksi",
    "laporan_pendapatan",
    "laporan_stok",
    "laporan_mekanik",
    "laporan_pembelian",
)

#: Username login yang TIDAK boleh muncul di halaman laporan.
USERNAME_TERLARANG = ("akunpelangganrahasia", "akunmekanikrahasia")


class LaporanTampilanTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="adm", password=SANDI, role=User.ROLE_ADMIN
        )
        self.pelanggan = Pelanggan.objects.create(
            user=User.objects.create_user(
                username=USERNAME_TERLARANG[0], password=SANDI,
                role=User.ROLE_PELANGGAN, first_name="Siti", last_name="Aminah",
            )
        )
        self.mekanik = Mekanik.objects.create(
            user=User.objects.create_user(
                username=USERNAME_TERLARANG[1], password=SANDI,
                role=User.ROLE_MEKANIK, first_name="Budi", last_name="Santoso",
            ),
            spesialisasi="Mesin",
        )
        motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1234 AA", merk="Honda",
            model_kendaraan="Beat", tahun=2021, jenis_motor="Matic",
            kapasitas_mesin=110,
        )
        TransaksiServis.objects.create(
            kode_transaksi="TRX-TAMPIL-1", status=TransaksiServis.STATUS_SELESAI,
            pelanggan=self.pelanggan, mekanik=self.mekanik, kendaraan=motor,
            total_biaya=Decimal("150000"),
        )
        Sparepart.objects.create(
            kode="SP-T1", nama="Oli Mesin", kategori="Pelumas",
            harga=Decimal("50000"), stok=1, stok_minimum=5,
        )
        self.client.force_login(self.admin)

    def _isi(self, nama):
        respons = self.client.get(reverse(nama))
        self.assertEqual(respons.status_code, 200, nama)
        return respons.content.decode()

    # ------------------------------------------------------------ tombol Cetak

    def test_tombol_cetak_ada_di_kelima_laporan(self):
        for nama in LIMA_LAPORAN:
            with self.subTest(laporan=nama):
                isi = self._isi(nama)
                self.assertIn("window.print()", isi, nama)
                self.assertIn("Cetak", isi, nama)

    # ------------------------------------------------------------- nama tampil

    def test_laporan_transaksi_memakai_nama_tampil(self):
        isi = self._isi("laporan_transaksi")
        self.assertIn("Siti Aminah", isi)
        self.assertIn("Budi Santoso", isi)
        self.assertIn("KT 1234 AA", isi)
        for terlarang in USERNAME_TERLARANG:
            self.assertNotIn(terlarang, isi)

    def test_laporan_mekanik_memakai_nama_tampil(self):
        isi = self._isi("laporan_mekanik")
        self.assertIn("Budi Santoso", isi)
        self.assertIn("Mesin", isi)
        for terlarang in USERNAME_TERLARANG:
            self.assertNotIn(terlarang, isi)

    # ------------------------------------------------------- format tanggal

    def test_tanggal_transaksi_memakai_format_indonesia(self):
        """Tanggal seragam dengan halaman lain: '26 Okt 2026', bukan '26/10/2026'."""
        self.assertIn("Okt 2026", self._isi("laporan_transaksi"))

    # ------------------------------------------------------- kepala dan filter

    def test_kepala_cetak_memuat_judul_dan_periode(self):
        isi = self._isi("laporan_transaksi")
        self.assertIn("laporan-cetak-kepala", isi)
        self.assertIn("Periode", isi)

    def test_form_filter_ditandai_supaya_bisa_disembunyikan_saat_cetak(self):
        for nama in LIMA_LAPORAN:
            with self.subTest(laporan=nama):
                self.assertIn("laporan-filter", self._isi(nama), nama)


class BerandaAdminTampilanTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="adm", password=SANDI, role=User.ROLE_ADMIN
        )
        pelanggan = Pelanggan.objects.create(
            user=User.objects.create_user(
                username="pel", password=SANDI, role=User.ROLE_PELANGGAN
            )
        )
        TransaksiServis.objects.create(
            pelanggan=pelanggan,
            kendaraan=Motor.objects.create(
                pelanggan=pelanggan, no_polisi="KT 9 QQ", merk="Honda",
                model_kendaraan="Vario", tahun=2022, jenis_motor="Matic",
                kapasitas_mesin=125,
            ),
            keluhan="menunggu konfirmasi pelanggan",
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
            status=TransaksiServis.STATUS_MENUNGGU_KONFIRMASI,
        )
        self.client.force_login(self.admin)

    def _kartu_laporan(self, isi):
        """Potong HTML tepat pada kartu 'Laporan' di kolom kanan beranda."""
        penanda = 'id="kartu-laporan"'
        self.assertIn(penanda, isi, "kartu Laporan tidak ditemukan di beranda")
        return isi.split(penanda, 1)[1].split("</div></div>", 1)[0]

    def test_kartu_laporan_memuat_kelima_tautan(self):
        kartu = self._kartu_laporan(
            self.client.get(reverse("admin_dashboard")).content.decode()
        )
        for nama in LIMA_LAPORAN:
            with self.subTest(laporan=nama):
                self.assertIn(reverse(nama), kartu, nama)

    def test_lencana_status_di_servis_terakhir_boleh_turun_baris(self):
        """Lencana panjang dulu terpotong jadi 'Menunggu Konfi…'; sekarang
        dibungkus supaya utuh."""
        isi = self.client.get(reverse("admin_dashboard")).content.decode()
        self.assertIn("badge-bungkus", isi)
