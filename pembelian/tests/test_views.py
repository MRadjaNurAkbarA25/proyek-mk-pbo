"""Uji tampilan FR-35: halaman Supplier dan Pembelian (role ADMIN)."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from pembelian.models import PembelianSparepart, Supplier
from sparepart.models import Sparepart

SANDI = "rahasia12345"


def buat_admin():
    return User.objects.create_user(username="adm", password=SANDI, role=User.ROLE_ADMIN)


def buat_kasir():
    return User.objects.create_user(username="kash", password=SANDI, role=User.ROLE_KASIR)


def buat_sparepart(kode, stok=0, harga=50000):
    return Sparepart.objects.create(
        kode=kode, nama=f"Barang {kode}", kategori="Oli",
        harga=harga, stok=stok, stok_minimum=5,
    )


def buat_supplier(nama="PT Sinar Jaya", aktif=True):
    return Supplier.objects.create(nama=nama, telepon="0812", alamat="Samarinda", aktif=aktif)


class AksesRoleTest(TestCase):
    """Halaman supplier dan pembelian khusus ADMIN."""

    def setUp(self):
        self.admin = buat_admin()
        self.url = reverse("pembelian:supplier_list")

    def test_admin_boleh_membuka(self):
        self.client.login(username="adm", password=SANDI)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_tanpa_login_diarahkan_ke_login(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith(reverse("login")))

    def test_kasir_ditolak(self):
        buat_kasir()
        self.client.login(username="kash", password=SANDI)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("dashboard"))


class SupplierTampilanTest(TestCase):
    def setUp(self):
        self.admin = buat_admin()
        self.client.login(username="adm", password=SANDI)

    def test_tambah_supplier_lewat_form(self):
        resp = self.client.post(reverse("pembelian:supplier_tambah"), {
            "nama": "PT Maju Mundur", "telepon": "0811", "alamat": "Balikpapan", "catatan": "",
        })
        self.assertRedirects(resp, reverse("pembelian:supplier_list"))
        self.assertTrue(Supplier.objects.filter(nama="PT Maju Mundur").exists())

    def test_nonaktifkan_supplier_lewat_tombol(self):
        s = buat_supplier()
        resp = self.client.post(
            reverse("pembelian:supplier_ubah_status", args=[s.pk]),
            {"aktif": "0", "next": reverse("pembelian:supplier_list")},
        )
        self.assertRedirects(resp, reverse("pembelian:supplier_list"))
        s.refresh_from_db()
        self.assertFalse(s.aktif)


class AlurPembelianTampilanTest(TestCase):
    """Alur penuh lewat client: catat draf -> tambah barang -> selesaikan."""

    def setUp(self):
        self.admin = buat_admin()
        self.client.login(username="adm", password=SANDI)
        self.supplier = buat_supplier()
        self.sp = buat_sparepart("VW-1", stok=0, harga=50000)
        self.sp2 = buat_sparepart("VW-2", stok=0, harga=20000)

    def _catat_draf(self):
        resp = self.client.post(reverse("pembelian:pembelian_catat"), {
            "supplier": self.supplier.pk,
            "tanggal": "2026-10-22",
            "metode_bayar": PembelianSparepart.METODE_TUNAI,
        })
        self.assertEqual(resp.status_code, 302)
        return PembelianSparepart.objects.get()

    def test_catat_draf_membuat_kode_dan_status_draf(self):
        p = self._catat_draf()
        self.assertEqual(p.status, PembelianSparepart.STATUS_DRAF)
        self.assertRegex(p.kode, r"^PB-20261022-\d{3}$")
        self.assertEqual(p.dicatat_oleh, self.admin)

    def test_alur_penuh_menambah_stok(self):
        p = self._catat_draf()
        self.client.post(reverse("pembelian:pembelian_tambah_barang", args=[p.pk]), {
            "sparepart": self.sp.pk, "jumlah": 3, "harga_beli": 40000,
        })
        self.client.post(reverse("pembelian:pembelian_tambah_barang", args=[p.pk]), {
            "sparepart": self.sp2.pk, "jumlah": 2, "harga_beli": 15000,
        })
        # Belum selesai: stok masih 0.
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.stok, 0)

        self.client.post(reverse("pembelian:pembelian_selesaikan", args=[p.pk]))
        self.sp.refresh_from_db()
        self.sp2.refresh_from_db()
        self.assertEqual(self.sp.stok, 3)
        self.assertEqual(self.sp2.stok, 2)
        p.refresh_from_db()
        self.assertEqual(p.status, PembelianSparepart.STATUS_SELESAI)
        self.assertEqual(p.total, Decimal("150000.00"))

    def test_hapus_draf_tidak_menambah_stok(self):
        p = self._catat_draf()
        self.client.post(reverse("pembelian:pembelian_tambah_barang", args=[p.pk]), {
            "sparepart": self.sp.pk, "jumlah": 3, "harga_beli": 40000,
        })
        self.client.post(reverse("pembelian:pembelian_hapus", args=[p.pk]))
        self.assertFalse(PembelianSparepart.objects.filter(pk=p.pk).exists())
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.stok, 0)

    def test_selesai_tidak_bisa_dihapus_lewat_url(self):
        p = self._catat_draf()
        self.client.post(reverse("pembelian:pembelian_tambah_barang", args=[p.pk]), {
            "sparepart": self.sp.pk, "jumlah": 1, "harga_beli": 40000,
        })
        self.client.post(reverse("pembelian:pembelian_selesaikan", args=[p.pk]))
        resp = self.client.post(reverse("pembelian:pembelian_hapus", args=[p.pk]))
        self.assertRedirects(resp, reverse("pembelian:pembelian_list"))
        self.assertTrue(PembelianSparepart.objects.filter(pk=p.pk).exists())

    def test_supplier_nonaktif_tidak_masuk_pilihan_form(self):
        nonaktif = buat_supplier("PT Tutup", aktif=False)
        resp = self.client.get(reverse("pembelian:pembelian_catat"))
        form = resp.context["form"]
        pk_terdaftar = [s.pk for s in form.fields["supplier"].queryset]
        self.assertNotIn(nonaktif.pk, pk_terdaftar)
        self.assertIn(self.supplier.pk, pk_terdaftar)

    def test_jumlah_nol_ditolak_di_form(self):
        p = self._catat_draf()
        self.client.post(reverse("pembelian:pembelian_tambah_barang", args=[p.pk]), {
            "sparepart": self.sp.pk, "jumlah": 0, "harga_beli": 40000,
        })
        self.assertEqual(p.detail.count(), 0)

    def test_tombol_beli_mengisi_sparepart_di_detail(self):
        """?sparepart=<pk> membuat draf meneruskan pk ke form tambah barang."""
        resp = self.client.post(
            reverse("pembelian:pembelian_catat") + f"?sparepart={self.sp.pk}",
            {
                "supplier": self.supplier.pk,
                "tanggal": "2026-10-22",
                "metode_bayar": PembelianSparepart.METODE_TUNAI,
            },
        )
        p = PembelianSparepart.objects.get()
        self.assertRedirects(resp, reverse("pembelian:pembelian_detail", args=[p.pk]) + f"?sparepart={self.sp.pk}")
        resp_detail = self.client.get(resp.url)
        self.assertEqual(
            str(resp_detail.context["form_tambah"]["sparepart"].value()), str(self.sp.pk)
        )