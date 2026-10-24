"""Uji penjagaan Django admin untuk FR-35.

Pembelian yang sudah SELESAI bersifat tetap: stoknya sudah bertambah sekali di
`PembelianSparepart.selesaikan()`. Berkas ini mengunci celah yang dulu terbuka
lewat `/admin/` (`pembelian/admin.py`):

  1. `status` bisa diubah SELESAI -> DRAF, lalu `selesaikan()` dipanggil lagi
     sehingga stok bertambah dua kali.
  2. Baris bisa ditambahkan ke pembelian SELESAI lewat inline maupun
     `DetailPembelianAdmin`, menghasilkan baris yatim dan total yang basi.
  3. Pembelian SELESAI bisa dihapus (tombol hapus maupun aksi massal).

Aturan yang sama sudah dijaga di `PembelianSparepart` (`_pastikan_draf`), jadi
tes di sini khusus pintu admin.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from pembelian.models import DetailPembelian, PembelianSparepart, Supplier
from sparepart.models import Sparepart

SANDI = "rahasia12345"


class AdminPembelianSelesaiTest(TestCase):
    def setUp(self):
        self.pengelola = User.objects.create_user(
            username="root",
            password=SANDI,
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.pengelola)

        self.sp = Sparepart.objects.create(
            kode="ADM-1", nama="Oli Mesin", kategori="Oli",
            harga=80000, stok=10, stok_minimum=2,
        )
        self.supplier = Supplier.objects.create(
            nama="PT Sinar Jaya", telepon="0812", alamat="Samarinda",
        )

        self.draf = self._buat_draf()
        self.draf.tambah_barang(self.sp, 2, Decimal("40000"))

        self.selesai = self._buat_draf()
        self.selesai.tambah_barang(self.sp, 3, Decimal("50000"))
        self.selesai.selesaikan()
        self.selesai.refresh_from_db()

    # --------------------------------------------------------------- bantuan
    def _buat_draf(self):
        return PembelianSparepart.objects.create(
            supplier=self.supplier,
            tanggal="2026-10-22",
            metode_bayar=PembelianSparepart.METODE_TUNAI,
            dicatat_oleh=self.pengelola,
        )

    def _url_ubah(self, pembelian):
        return reverse("admin:pembelian_pembeliansparepart_change", args=[pembelian.pk])

    def _url_hapus(self, pembelian):
        return reverse("admin:pembelian_pembeliansparepart_delete", args=[pembelian.pk])

    def _url_ubah_baris(self, baris):
        return reverse("admin:pembelian_detailpembelian_change", args=[baris.pk])

    def _url_hapus_baris(self, baris):
        return reverse("admin:pembelian_detailpembelian_delete", args=[baris.pk])

    def _stok(self):
        self.sp.refresh_from_db()
        return self.sp.stok

    # ------------------------------------------------- 1. status tidak bisa diubah
    def test_status_tidak_tersedia_di_form_ubah(self):
        resp = self.client.get(self._url_ubah(self.draf))
        self.assertEqual(resp.status_code, 200)
        form = resp.context["adminform"].form
        self.assertNotIn("status", form.fields)
        # Kolom lain tetap bisa disunting selama masih draf.
        self.assertIn("supplier", form.fields)

    def test_status_tidak_bisa_dikembalikan_ke_draf_lewat_post(self):
        stok_awal = self._stok()
        resp = self.client.post(
            self._url_ubah(self.selesai),
            {
                "supplier": self.supplier.pk,
                "tanggal": "2026-10-22",
                "metode_bayar": PembelianSparepart.METODE_TUNAI,
                "dicatat_oleh": self.pengelola.pk,
                "status": PembelianSparepart.STATUS_DRAF,  # dipaksa lewat POST
                "_save": "Simpan",
            },
        )
        self.assertEqual(resp.status_code, 403)  # POST ditolak, bukan disimpan
        self.selesai.refresh_from_db()
        self.assertEqual(self.selesai.status, PembelianSparepart.STATUS_SELESAI)

        # Kalau status sempat jadi DRAF, panggilan ini akan menambah stok lagi.
        with self.assertRaises(Exception):
            self.selesai.selesaikan()
        self.assertEqual(self._stok(), stok_awal)

    def test_seluruh_field_selesai_hanya_baca(self):
        resp = self.client.get(self._url_ubah(self.selesai))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["adminform"].form.fields, {})

    # ------------------------------------------------- 2. baris tidak bisa ditambah
    def test_inline_tidak_menawarkan_tambah_baris_pada_selesai(self):
        resp = self.client.get(self._url_ubah(self.selesai))
        self.assertEqual(resp.status_code, 200)
        isi = resp.content.decode()
        # Tanpa has_add_permission, template baris kosong tidak dirender.
        self.assertNotIn("detail-__prefix__", isi)
        # Tanpa has_delete_permission, kotak centang hapus tidak dirender.
        self.assertNotIn('name="detail-0-DELETE"', isi)

    def test_post_inline_pada_selesai_tidak_membuat_baris(self):
        jumlah_awal = self.selesai.detail.count()
        total_awal = self.selesai.total
        self.client.post(
            self._url_ubah(self.selesai),
            {
                "supplier": self.supplier.pk,
                "tanggal": "2026-10-22",
                "metode_bayar": PembelianSparepart.METODE_TUNAI,
                "dicatat_oleh": self.pengelola.pk,
                "detail-TOTAL_FORMS": "1",
                "detail-INITIAL_FORMS": "0",
                "detail-MIN_NUM_FORMS": "0",
                "detail-MAX_NUM_FORMS": "1000",
                "detail-0-sparepart": self.sp.pk,
                "detail-0-jumlah": "5",
                "detail-0-harga_satuan": "1000",
                "_save": "Simpan",
            },
        )
        self.assertEqual(self.selesai.detail.count(), jumlah_awal)
        self.selesai.refresh_from_db()
        self.assertEqual(self.selesai.total, total_awal)

    def test_induk_selesai_tidak_ditawarkan_di_form_baris_baru(self):
        resp = self.client.get(reverse("admin:pembelian_detailpembelian_add"))
        self.assertEqual(resp.status_code, 200)
        pilihan = resp.context["adminform"].form.fields["pembelian"].queryset
        self.assertIn(self.draf, pilihan)
        self.assertNotIn(self.selesai, pilihan)

    def test_baris_selesai_hanya_bisa_dilihat(self):
        baris = self.selesai.detail.get()
        resp = self.client.get(self._url_ubah_baris(baris))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["adminform"].form.fields, {})

        resp = self.client.post(
            self._url_ubah_baris(baris),
            {"pembelian": self.selesai.pk, "sparepart": self.sp.pk,
             "jumlah": "99", "harga_satuan": "1", "_save": "Simpan"},
        )
        self.assertEqual(resp.status_code, 403)
        baris.refresh_from_db()
        self.assertEqual(baris.jumlah, 3)
        self.assertEqual(baris.harga_satuan, Decimal("50000.00"))

    def test_baris_selesai_tidak_bisa_dihapus(self):
        baris = self.selesai.detail.get()
        resp = self.client.get(self._url_hapus_baris(baris))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(DetailPembelian.objects.filter(pk=baris.pk).exists())

    # ------------------------------------------------------- 3. tidak bisa dihapus
    def test_pembelian_selesai_tidak_bisa_dihapus(self):
        resp = self.client.get(self._url_hapus(self.selesai))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(PembelianSparepart.objects.filter(pk=self.selesai.pk).exists())

    def test_pembelian_draf_masih_bisa_dihapus(self):
        resp = self.client.get(self._url_hapus(self.draf))
        self.assertEqual(resp.status_code, 200)

    def _aksi_tersedia(self, url):
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        form = resp.context["action_form"]
        return [nama for nama, _ in form.fields["action"].choices]

    def test_delete_selected_bawaan_tidak_dipakai(self):
        # Aksi bawaan membatalkan seluruh pilihan kalau ada satu yang terkunci,
        # jadi diganti aksi yang menyaring sendiri.
        aksi = self._aksi_tersedia(reverse("admin:pembelian_pembeliansparepart_changelist"))
        self.assertNotIn("delete_selected", aksi)
        self.assertIn("hapus_draf_terpilih", aksi)

        aksi = self._aksi_tersedia(reverse("admin:pembelian_detailpembelian_changelist"))
        self.assertNotIn("delete_selected", aksi)
        self.assertIn("hapus_baris_draf_terpilih", aksi)

    def test_aksi_massal_tetap_menghapus_draf(self):
        stok_awal = self._stok()
        self.client.post(
            reverse("admin:pembelian_pembeliansparepart_changelist"),
            {
                "action": "hapus_draf_terpilih",
                "_selected_action": [self.draf.pk, self.selesai.pk],
            },
        )
        self.assertFalse(PembelianSparepart.objects.filter(pk=self.draf.pk).exists())
        self.assertTrue(PembelianSparepart.objects.filter(pk=self.selesai.pk).exists())
        self.assertEqual(self._stok(), stok_awal)

    def test_aksi_massal_baris_tetap_menghapus_draf(self):
        baris_selesai = self.selesai.detail.get()
        baris_draf = self.draf.detail.get()
        self.client.post(
            reverse("admin:pembelian_detailpembelian_changelist"),
            {
                "action": "hapus_baris_draf_terpilih",
                "_selected_action": [baris_draf.pk, baris_selesai.pk],
            },
        )
        self.assertFalse(DetailPembelian.objects.filter(pk=baris_draf.pk).exists())
        self.assertTrue(DetailPembelian.objects.filter(pk=baris_selesai.pk).exists())

    # ---------------------------------------- 4. total ikut berubah lewat admin
    def test_hapus_baris_draf_lewat_admin_memperbarui_total(self):
        baris = self.draf.detail.get()
        self.client.post(self._url_hapus_baris(baris), {"post": "yes"})
        self.draf.refresh_from_db()
        self.assertEqual(self.draf.total, Decimal("0"))

    def test_ubah_baris_draf_lewat_admin_memperbarui_total(self):
        baris = self.draf.detail.get()
        self.client.post(
            self._url_ubah_baris(baris),
            {"pembelian": self.draf.pk, "sparepart": self.sp.pk,
             "jumlah": "5", "harga_satuan": "40000", "_save": "Simpan"},
        )
        baris.refresh_from_db()
        self.draf.refresh_from_db()
        self.assertEqual(baris.subtotal, Decimal("200000.00"))
        self.assertEqual(self.draf.total, Decimal("200000.00"))


class AdminSupplierTanpaHapusTest(TestCase):
    """FR-35: supplier tidak dihapus, hanya dinonaktifkan lewat kolom "aktif"."""

    def setUp(self):
        self.pengelola = User.objects.create_user(
            username="root2", password=SANDI, role=User.ROLE_ADMIN,
            is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.pengelola)
        self.supplier = Supplier.objects.create(nama="CV Abadi", telepon="0813")

    def _model_admin(self):
        from django.contrib import admin as django_admin

        return django_admin.site._registry[Supplier]

    def test_permission_hapus_selalu_false(self):
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = self.pengelola
        model_admin = self._model_admin()
        # Tanpa objek (changelist) maupun dengan objek (form ubah).
        self.assertFalse(model_admin.has_delete_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request, self.supplier))

    def test_url_hapus_ditolak(self):
        response = self.client.get(
            reverse("admin:pembelian_supplier_delete", args=[self.supplier.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Supplier.objects.filter(pk=self.supplier.pk).exists())

    def test_aksi_hapus_massal_tidak_tersedia(self):
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = self.pengelola
        aksi = self._model_admin().get_actions(request)
        self.assertNotIn("delete_selected", aksi)

    def test_nonaktifkan_tetap_jalan_lewat_admin(self):
        self.client.post(
            reverse("admin:pembelian_supplier_change", args=[self.supplier.pk]),
            {"nama": "CV Abadi", "telepon": "0813", "alamat": "", "catatan": "", "_save": "Simpan"},
        )
        self.supplier.refresh_from_db()
        self.assertTrue(Supplier.objects.filter(pk=self.supplier.pk).exists())
