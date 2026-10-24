"""Uji pencabutan kolom stok dari form sparepart (FR-35).

Setelah FR-35, stok tidak boleh lagi diketik manual di form sparepart:
stok bertambah lewat Pembelian dan berkurang saat dipakai servis. Uji ini
memastikan kolom 'stok' benar-benar hilang dan stok tidak berubah lewat
form tambah/ubah.
"""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from sparepart.forms import SparepartForm
from sparepart.models import Sparepart

SANDI = "rahasia12345"


def buat(kode, stok=0, harga=50000):
    return Sparepart.objects.create(
        kode=kode, nama=f"Barang {kode}", kategori="Oli",
        harga=harga, stok=stok, stok_minimum=5,
    )


class FormTanpaStokTest(TestCase):
    def test_form_tidak_memuat_kolom_stok(self):
        self.assertNotIn("stok", SparepartForm().fields)

    def test_form_memuat_kolom_lainnya(self):
        fields = SparepartForm().fields
        self.assertIn("kode", fields)
        self.assertIn("nama", fields)
        self.assertIn("kategori", fields)
        self.assertIn("harga", fields)
        self.assertIn("stok_minimum", fields)

    def test_sparepart_baru_lahir_dengan_stok_nol(self):
        sp = Sparepart.objects.create(
            kode="NOL-1", nama="Barang Baru", kategori="Oli",
            harga=50000, stok_minimum=5,
        )
        self.assertEqual(sp.stok, 0)


class FormTanpaStokTampilanTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="adm", password=SANDI, role=User.ROLE_ADMIN)
        self.client.login(username="adm", password=SANDI)

    def test_tambah_sparepart_tanpa_stok(self):
        resp = self.client.post(reverse("sparepart:sparepart_create"), {
            "kode": "TPL-1", "nama": "Oli Baru", "kategori": "Oli",
            "harga": "60000", "stok_minimum": "5",
        })
        self.assertRedirects(resp, reverse("sparepart:sparepart_list"))
        sp = Sparepart.objects.get(kode="TPL-1")
        self.assertEqual(sp.stok, 0)

    def test_ubah_sparepart_tidak_mengubah_stok_yang_ada(self):
        sp = buat("UBAH-1", stok=7)
        resp = self.client.post(reverse("sparepart:sparepart_update", args=[sp.pk]), {
            "kode": "UBAH-1", "nama": "Oli Diubah", "kategori": "Oli",
            "harga": "65000", "stok_minimum": "5",
        })
        self.assertRedirects(resp, reverse("sparepart:sparepart_list"))
        sp.refresh_from_db()
        self.assertEqual(sp.stok, 7)

class AdminDjangoTanpaStokTest(TestCase):
    """Fase 4 FR-35: /admin/ juga bukan jalan pintas mengubah stok."""

    def test_stok_hanya_baca_di_admin(self):
        su = User.objects.create_superuser("root", "root@contoh.id", SANDI)
        self.client.force_login(su)
        sp = buat("ADM-1", stok=7)
        resp = self.client.get(reverse("admin:sparepart_sparepart_change", args=[sp.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'name="stok"')
