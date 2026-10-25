"""Uji tiga tingkat kondisi stok sparepart (FR-23).

Yang paling mudah salah di sini adalah batas-batasnya: stok tepat 0, stok
tepat sama dengan stok_minimum, dan stok satu di atas minimum. Ketiganya
diuji satu per satu.
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from sparepart.models import Sparepart

SANDI = "rahasia12345"


def buat(kode, stok, minimum=5):
    return Sparepart.objects.create(
        kode=kode, nama=f"Barang {kode}", kategori="Oli",
        harga=50000, stok=stok, stok_minimum=minimum,
    )


class StatusStokTest(TestCase):
    def test_stok_nol_berstatus_kosong(self):
        sp = buat("A1", stok=0)
        self.assertEqual(sp.status_stok, Sparepart.STOK_KOSONG)
        self.assertEqual(sp.label_stok, "Stok Kosong")
        self.assertTrue(sp.stok_habis)

    def test_stok_satu_sudah_bukan_kosong(self):
        """Batas terpenting: 1 masih bisa dipakai servis, 0 tidak."""
        sp = buat("A2", stok=1)
        self.assertEqual(sp.status_stok, Sparepart.STOK_MINIM)
        self.assertFalse(sp.stok_habis)

    def test_stok_tepat_di_batas_minimum_berstatus_minim(self):
        sp = buat("A3", stok=5, minimum=5)
        self.assertEqual(sp.status_stok, Sparepart.STOK_MINIM)
        self.assertEqual(sp.label_stok, "Stok Minim")

    def test_stok_satu_di_atas_minimum_sudah_aman(self):
        sp = buat("A4", stok=6, minimum=5)
        self.assertEqual(sp.status_stok, Sparepart.STOK_AMAN)
        self.assertEqual(sp.label_stok, "Aman")

    def test_stok_minimum_nol_membuat_stok_satu_tetap_aman(self):
        """Kalau minimumnya disetel 0, hanya stok 0 yang dianggap bermasalah."""
        self.assertEqual(buat("A5", stok=0, minimum=0).status_stok, Sparepart.STOK_KOSONG)
        self.assertEqual(buat("A6", stok=1, minimum=0).status_stok, Sparepart.STOK_AMAN)

    def test_stok_minus_tetap_dihitung_kosong(self):
        """Tidak seharusnya terjadi, tapi stok tidak boleh lolos jadi 'Aman'."""
        sp = buat("A7", stok=-3)
        self.assertEqual(sp.status_stok, Sparepart.STOK_KOSONG)

    # is_stok_kritis dipakai mekanik, laporan stok, dan kartu dashboard,
    # jadi artinya tidak boleh berubah: kosong DAN minim sama-sama kritis.
    def test_is_stok_kritis_mencakup_kosong_dan_minim(self):
        self.assertTrue(buat("B1", stok=0).is_stok_kritis)
        self.assertTrue(buat("B2", stok=5, minimum=5).is_stok_kritis)
        self.assertFalse(buat("B3", stok=6, minimum=5).is_stok_kritis)

    def test_kurangi_stok_sampai_habis_mengubah_status(self):
        sp = buat("C1", stok=2, minimum=1)
        sp.kurangi_stok(2)
        sp.refresh_from_db()
        self.assertEqual(sp.status_stok, Sparepart.STOK_KOSONG)


class TampilanStatusStokTest(TestCase):
    def setUp(self):
        User.objects.create_user(username="adm", password=SANDI, role=User.ROLE_ADMIN)
        self.client.login(username="adm", password=SANDI)
        buat("K1", stok=0)        # kosong
        buat("M1", stok=3)        # minim
        buat("S1", stok=50)       # aman

    def test_ketiga_label_muncul_di_daftar_sparepart(self):
        isi = self.client.get(reverse("sparepart:sparepart_list")).content.decode()
        self.assertIn("Stok Kosong", isi)
        self.assertIn("Stok Minim", isi)
        self.assertIn("Aman", isi)

    def test_warna_badge_sesuai_tingkatnya(self):
        isi = self.client.get(reverse("sparepart:sparepart_list")).content.decode()
        # Tabel bersama memakai lencana .badge-st (tabel.css), bukan badge Bootstrap.
        self.assertIn('badge-st merah">Stok Kosong', isi)
        self.assertIn('badge-st kuning">Stok Minim', isi)
        self.assertIn('badge-st hijau">Aman', isi)

    def test_peringatan_memberitahu_berapa_yang_habis(self):
        isi = self.client.get(reverse("sparepart:sparepart_list")).content.decode()
        self.assertIn("1 sparepart stoknya <strong>habis</strong>", isi)
        self.assertIn("1 lagi sudah menipis", isi)

    def test_peringatan_kuning_kalau_tidak_ada_yang_habis(self):
        Sparepart.objects.filter(kode="K1").update(stok=99)
        isi = self.client.get(reverse("sparepart:sparepart_list")).content.decode()
        self.assertIn("alert alert-warning", isi)
        self.assertNotIn("alert alert-danger", isi)

    def test_halaman_peringatan_menaruh_yang_habis_paling_atas(self):
        daftar = self.client.get(reverse("sparepart:peringatan_stok")).context["spareparts"]
        self.assertEqual([s.kode for s in daftar], ["K1", "M1"])

    def test_sparepart_aman_tidak_masuk_halaman_peringatan(self):
        daftar = self.client.get(reverse("sparepart:peringatan_stok")).context["spareparts"]
        self.assertNotIn("S1", [s.kode for s in daftar])

    def test_kartu_dashboard_memisahkan_jumlah_habis(self):
        konteks = self.client.get(reverse("admin_dashboard")).context
        self.assertEqual(konteks["sparepart_kritis"], 2)
        self.assertEqual(konteks["sparepart_kosong"], 1)

    def test_laporan_stok_admin_memakai_badge_yang_sama(self):
        isi = self.client.get(reverse("laporan_stok")).content.decode()
        self.assertIn('text-bg-danger">Stok Kosong', isi)
        self.assertIn('text-bg-warning">Stok Minim', isi)
