"""Uji model FR-35: Supplier, PembelianSparepart, DetailPembelian.

Fokus pada aturan bisnis yang paling mudah salah:
  - stok TIDAK berubah saat masih draf, baru bertambah saat "Selesaikan"
  - pembelian kosong ditolak
  - pembelian yang sudah SELESAI tidak bisa diubah/dihapus
  - harga beli & jumlah harus > 0
  - kode pembelian berformat PB-YYYYMMDD-NNN
  - pewarisan BarisTransaksi (NFR-4: abstraction + inheritance)
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from accounts.models import User
from pembelian.models import DetailPembelian, PembelianSparepart, Supplier
from sparepart.models import BarisTransaksi, DetailSparepart, Sparepart

SANDI = "rahasia12345"


def buat_sparepart(kode, stok=0, harga=50000):
    return Sparepart.objects.create(
        kode=kode, nama=f"Barang {kode}", kategori="Oli",
        harga=harga, stok=stok, stok_minimum=5,
    )


def buat_supplier(nama="PT Sinar Jaya", aktif=True):
    return Supplier.objects.create(nama=nama, telepon="0812", alamat="Samarinda", aktif=aktif)


class PewarisanBarisTransaksiTest(TestCase):
    """NFR-4: DetailPembelian dan DetailSparepart mewarisi class abstrak yang sama."""

    def test_baris_transaksi_abstrak(self):
        self.assertTrue(BarisTransaksi._meta.abstract)

    def test_detail_pembelian_mewarisi_baris_transaksi(self):
        self.assertTrue(issubclass(DetailPembelian, BarisTransaksi))

    def test_detail_sparepart_mewarisi_baris_transaksi(self):
        self.assertTrue(issubclass(DetailSparepart, BarisTransaksi))

    def test_hitung_subtotal_dipakai_keduanya(self):
        # Polymorphism: method yang sama menghasilkan subtotal untuk dua detail
        # yang harga dasarnya berbeda (harga jual vs harga beli).
        sp = buat_sparepart("POLY-1", harga=50000)
        barang = DetailPembelian(sparepart=sp, jumlah=2, harga_satuan=40000)
        self.assertEqual(barang.hitung_subtotal(), Decimal("80000.00"))


class KodePembelianTest(TestCase):
    def test_kode_berformat_pb_tanggal_nomor(self):
        pembelian = PembelianSparepart.objects.create(
            supplier=buat_supplier(), tanggal="2026-10-22",
            metode_bayar=PembelianSparepart.METODE_TUNAI,
            dicatat_oleh=User.objects.create_user(username="adm", password=SANDI, role=User.ROLE_ADMIN),
        )
        self.assertRegex(pembelian.kode, r"^PB-20261022-\d{3}$")


class AlurPembelianTest(TestCase):
    """Stok hanya berubah saat 'Selesaikan'. Ini inti FR-35."""

    def setUp(self):
        self.admin = User.objects.create_user(username="adm", password=SANDI, role=User.ROLE_ADMIN)
        self.supplier = buat_supplier()
        self.sp = buat_sparepart("ALUR-1", stok=0, harga=50000)

    def _buat_draf(self, **kw):
        return PembelianSparepart.objects.create(
            supplier=self.supplier, tanggal="2026-10-22",
            metode_bayar=PembelianSparepart.METODE_TUNAI,
            dicatat_oleh=self.admin, **kw,
        )

    def test_tambah_barang_tidak_mengubah_stok(self):
        p = self._buat_draf()
        p.tambah_barang(self.sp, jumlah=3, harga_beli=40000)
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.stok, 0)
        self.assertEqual(p.status, PembelianSparepart.STATUS_DRAF)

    def test_selesai_menambah_stok_dan_status(self):
        p = self._buat_draf()
        p.tambah_barang(self.sp, jumlah=3, harga_beli=40000)
        p.selesaikan()
        self.sp.refresh_from_db()
        p.refresh_from_db()
        self.assertEqual(self.sp.stok, 3)
        self.assertEqual(p.status, PembelianSparepart.STATUS_SELESAI)

    def test_subtotal_dan_total_dihitung(self):
        p = self._buat_draf()
        p.tambah_barang(self.sp, jumlah=3, harga_beli=40000)
        barang = p.detail.get()
        self.assertEqual(barang.subtotal, Decimal("120000.00"))
        self.assertEqual(p.total, Decimal("120000.00"))

    def test_total_menjumlahkan_beberapa_barang(self):
        sp2 = buat_sparepart("ALUR-2", stok=0, harga=10000)
        p = self._buat_draf()
        p.tambah_barang(self.sp, jumlah=2, harga_beli=40000)
        p.tambah_barang(sp2, jumlah=1, harga_beli=10000)
        p.refresh_from_db()
        self.assertEqual(p.total, Decimal("90000.00"))

    def test_hapus_barang_mengurangi_total(self):
        sp2 = buat_sparepart("ALUR-3", stok=0, harga=10000)
        p = self._buat_draf()
        p.tambah_barang(self.sp, jumlah=2, harga_beli=40000)
        p.tambah_barang(sp2, jumlah=1, harga_beli=10000)
        p.hapus_barang(p.detail.get(sparepart=sp2))
        p.refresh_from_db()
        self.assertEqual(p.total, Decimal("80000.00"))


class LaranganAlurTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="adm", password=SANDI, role=User.ROLE_ADMIN)
        self.supplier = buat_supplier()
        self.sp = buat_sparepart("LARANG-1", stok=0, harga=50000)

    def _draf(self):
        return PembelianSparepart.objects.create(
            supplier=self.supplier, tanggal="2026-10-22",
            metode_bayar=PembelianSparepart.METODE_TUNAI, dicatat_oleh=self.admin,
        )

    def test_pembelian_kosong_tidak_bisa_diselesaikan(self):
        p = self._draf()
        with self.assertRaises(ValidationError):
            p.selesaikan()

    def test_jumlah_nol_ditolak(self):
        p = self._draf()
        with self.assertRaises(ValidationError):
            p.tambah_barang(self.sp, jumlah=0, harga_beli=40000)

    def test_harga_beli_nol_ditolak(self):
        p = self._draf()
        with self.assertRaises(ValidationError):
            p.tambah_barang(self.sp, jumlah=2, harga_beli=0)

    def test_baris_langsung_dengan_jumlah_atau_harga_nol_ditolak(self):
        """Aturan > 0 dijaga model, bukan hanya tambah_barang (jalur /admin/)."""
        p = self._draf()
        for jumlah, harga in ((0, 40000), (2, 0), (2, -1)):
            with self.assertRaises(ValidationError):
                DetailPembelian.objects.create(pembelian=p, sparepart=self.sp, jumlah=jumlah, harga_satuan=harga)
        self.assertFalse(p.detail.exists())

    def test_supplier_nonaktif_tidak_bisa_dipilih(self):
        nonaktif = buat_supplier("PT Tutup", aktif=False)
        with self.assertRaises(ValidationError):
            PembelianSparepart.objects.create(supplier=nonaktif, metode_bayar=PembelianSparepart.METODE_TUNAI)
        p = self._draf()
        p.supplier = nonaktif
        with self.assertRaises(ValidationError):
            p.save()

    def test_draf_tetap_bisa_selesai_walau_supplier_dinonaktifkan(self):
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=2, harga_beli=40000)
        self.supplier.nonaktifkan()
        p.selesaikan()
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.stok, 2)

    def test_selesai_tidak_bisa_ditambah_barang_lagi(self):
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)
        p.selesaikan()
        with self.assertRaises(ValidationError):
            p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)

    def test_selesai_tidak_bisa_dihapus(self):
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)
        p.selesaikan()
        with self.assertRaises(ValidationError):
            p.hapus_draf()

    def test_selesai_tidak_bisa_dihapus_lewat_delete(self):
        """`hapus_draf()` bukan satu-satunya pintu; `delete()` juga dijaga."""
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)
        p.selesaikan()
        with self.assertRaises(ValidationError):
            p.delete()
        self.assertTrue(PembelianSparepart.objects.filter(pk=p.pk).exists())

    def test_draf_masih_bisa_dihapus_lewat_delete(self):
        p = self._draf()
        p.delete()
        self.assertFalse(PembelianSparepart.objects.filter(pk=p.pk).exists())

    def test_baris_pada_pembelian_selesai_tidak_bisa_dihapus(self):
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)
        p.selesaikan()
        baris = p.detail.get()
        with self.assertRaises(ValidationError):
            baris.delete()
        self.assertTrue(DetailPembelian.objects.filter(pk=baris.pk).exists())

    def test_selesai_tidak_bisa_dikembalikan_ke_draf(self):
        """Tanpa penjagaan ini, status bisa dibalik lalu `selesaikan()` diulang."""
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)
        p.selesaikan()
        stok_setelah_selesai = Sparepart.objects.get(pk=self.sp.pk).stok

        p.status = PembelianSparepart.STATUS_DRAF
        with self.assertRaises(ValidationError):
            p.save(update_fields=["status"])

        p.refresh_from_db()
        self.assertEqual(p.status, PembelianSparepart.STATUS_SELESAI)
        with self.assertRaises(ValidationError):
            p.selesaikan()
        self.assertEqual(Sparepart.objects.get(pk=self.sp.pk).stok, stok_setelah_selesai)

    def test_hapus_massal_pembelian_ditolak(self):
        p = self._draf()
        with self.assertRaises(ValidationError):
            PembelianSparepart.objects.filter(pk=p.pk).delete()
        self.assertTrue(PembelianSparepart.objects.filter(pk=p.pk).exists())

    def test_hapus_massal_baris_ditolak(self):
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)
        with self.assertRaises(ValidationError):
            DetailPembelian.objects.filter(pembelian=p).delete()
        self.assertEqual(p.detail.count(), 1)

    def test_selesai_tidak_bisa_diselesaikan_dua_kali(self):
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=1, harga_beli=40000)
        p.selesaikan()
        with self.assertRaises(ValidationError):
            p.selesaikan()

    def test_klik_ganda_dengan_objek_basi_tidak_menambah_stok_dua_kali(self):
        """Dua request memuat draf yang sama sebelum salah satunya selesai."""
        p = self._draf()
        p.tambah_barang(self.sp, jumlah=5, harga_beli=40000)
        klik_1 = PembelianSparepart.objects.get(pk=p.pk)
        klik_2 = PembelianSparepart.objects.get(pk=p.pk)
        klik_1.selesaikan()
        with self.assertRaises(ValidationError):
            klik_2.selesaikan()
        self.assertEqual(Sparepart.objects.get(pk=self.sp.pk).stok, 5)


class SupplierTest(TestCase):
    def test_tambah_baru_langsung_aktif(self):
        self.assertTrue(buat_supplier().aktif)

    def test_nonaktifkan_dan_aktifkan(self):
        s = buat_supplier()
        s.nonaktifkan()
        self.assertFalse(s.aktif)
        s.aktifkan()
        self.assertTrue(s.aktif)

    def test_nonaktifkan_supplier_yang_sudah_nonaktif_ditolak(self):
        s = buat_supplier(aktif=False)
        with self.assertRaises(ValidationError):
            s.nonaktifkan()

    def test_supplier_tidak_bisa_dihapus(self):
        """FR-35: supplier tidak dihapus, hanya dinonaktifkan."""
        s = buat_supplier()
        with self.assertRaises(ValidationError):
            s.delete()
        self.assertTrue(Supplier.objects.filter(pk=s.pk).exists())

    def test_supplier_dipilih_pembelian_tidak_bisa_dihapus(self):
        """Penghapusan massal pun ditolak; PROTECT tetap jadi lapisan database."""
        s = buat_supplier()
        PembelianSparepart.objects.create(
            supplier=s, tanggal="2026-10-22", metode_bayar=PembelianSparepart.METODE_TUNAI,
        )
        with self.assertRaises(ValidationError):
            Supplier.objects.filter(pk=s.pk).delete()
        self.assertIs(
            PembelianSparepart._meta.get_field("supplier").remote_field.on_delete,
            models.PROTECT,
        )