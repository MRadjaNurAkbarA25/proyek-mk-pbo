"""Komponen tabel bersama (static/css/tabel.css) dan tombol aksi ikon.

Gaya tabel Riwayat Servis pelanggan dipakai ulang di halaman admin, kasir,
dan mekanik. Supaya tidak ada salinan gaya per halaman, gayanya dipindah ke
satu berkas yang dimuat ketiga kerangka. Tombol ubah/hapus jadi ikon pensil
dan tong sampah lewat partial _aksi_ubah.html dan _aksi_hapus.html.
"""
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import Mekanik, Pelanggan, User


class CssTabelDimuatSemuaKerangka(TestCase):
    def test_kerangka_admin_pelanggan_mekanik(self):
        admin = User.objects.create_user(username="adm", password="x", role=User.ROLE_ADMIN)
        pelanggan = User.objects.create_user(username="plg", password="x", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=pelanggan)
        mekanik = User.objects.create_user(username="mek", password="x", role=User.ROLE_MEKANIK)
        Mekanik.objects.create(user=mekanik, status=Mekanik.STATUS_TERSEDIA)
        for user, url in ((admin, reverse("kelola_kasir")),
                          (pelanggan, reverse("riwayat_service")),
                          (mekanik, reverse("mekanik_dashboard"))):
            self.client.force_login(user)
            with self.subTest(role=user.role):
                self.assertContains(self.client.get(url), "css/tabel.css")


class PartialTombolIkon(TestCase):
    def render(self, isi):
        request = RequestFactory().get("/")
        return Template(isi).render(Context({"request": request, "csrf_token": "tok"}))

    def test_tombol_ubah_berupa_ikon_pensil(self):
        html = self.render('{% include "_aksi_ubah.html" with url="/x/1/ubah/" label="Ubah Wati" %}')
        self.assertIn('href="/x/1/ubah/"', html)
        self.assertIn("#i-ubah", html)
        self.assertIn('title="Ubah Wati"', html)
        self.assertIn('aria-label="Ubah Wati"', html)

    def test_tombol_hapus_tetap_minta_konfirmasi(self):
        html = self.render(
            '{% include "_aksi_hapus.html" with url="/x/1/hapus/" label="Hapus Oli" '
            'pesan="Oli akan dihapus." judul="Hapus sparepart?" %}')
        self.assertIn('method="post"', html)
        self.assertIn('action="/x/1/hapus/"', html)
        self.assertIn('data-konfirmasi="Oli akan dihapus."', html)
        self.assertIn('data-konfirmasi-judul="Hapus sparepart?"', html)
        self.assertIn("#i-hapus", html)
        self.assertIn('aria-label="Hapus Oli"', html)
        self.assertIn("csrfmiddlewaretoken", html)


class HalamanMemakaiTabelBersama(TestCase):
    """Semua tabel daftar admin + Riwayat Terakhir mekanik memakai .tabel-data.

    Halaman laporan (Laras) dan halaman kasir (Alya) sengaja tidak termasuk.
    """

    def setUp(self):
        import io
        from django.core.management import call_command
        call_command("seed_demo", verbosity=0, stdout=io.StringIO(), izinkan_di_server=True)
        from sparepart.models import Sparepart
        self.sp = Sparepart.objects.order_by("pk").first()
        self.sp.stok = 0  # supaya ada di Peringatan Stok dan punya tombol Beli
        self.sp.save()
        self.client.force_login(User.objects.get(username="admin1"))

    def ambil(self, url):
        respons = self.client.get(url)
        self.assertEqual(respons.status_code, 200, url)
        self.assertContains(respons, 'class="tabel-data', msg_prefix=url)
        self.assertNotContains(respons, "table-dark", msg_prefix=url)
        self.assertNotContains(respons, 'class="table ', msg_prefix=url)
        return respons

    def test_daftar_admin(self):
        for nama in ("admin_dashboard", "sparepart:sparepart_list", "sparepart:peringatan_stok",
                     "kelola_mekanik", "kelola_kasir", "kelola_pelanggan", "kelola_kendaraan",
                     "kelola_jenis", "pembelian:supplier_list", "pembelian:pembelian_list", "kelola_faq"):
            with self.subTest(halaman=nama):
                self.ambil(reverse(nama))

    def test_tombol_teks_ubah_hapus_jadi_ikon(self):
        for nama in ("sparepart:sparepart_list", "kelola_mekanik", "kelola_kasir", "kelola_pelanggan",
                     "kelola_jenis", "pembelian:supplier_list", "kelola_faq"):
            with self.subTest(halaman=nama):
                respons = self.ambil(reverse(nama))
                self.assertContains(respons, "#i-ubah")
                self.assertNotContains(respons, ">Ubah<")
                self.assertNotContains(respons, ">Hapus<")

    def test_hapus_sparepart_lewat_ikon_dengan_konfirmasi(self):
        respons = self.ambil(reverse("sparepart:sparepart_list"))
        self.assertContains(respons, f'action="{reverse("sparepart:sparepart_delete", args=[self.sp.pk])}"')
        self.assertContains(respons, "#i-hapus")
        self.assertContains(respons, "data-konfirmasi=")
        # Tombol Beli untuk stok kritis tetap ada.
        self.assertContains(respons, f'{reverse("pembelian:pembelian_catat")}?sparepart={self.sp.pk}')

    def test_hapus_jenis_servis_lewat_ikon(self):
        from mekanik.models import JenisServis
        jenis = JenisServis.objects.order_by("pk").first()
        respons = self.ambil(reverse("kelola_jenis"))
        self.assertContains(respons, f'action="{reverse("kelola_jenis_hapus", args=[jenis.pk])}"')

    def test_mekanik_tanpa_riwayat_punya_ikon_hapus(self):
        baru = User.objects.create_user(username="mekbaru", password="x", role=User.ROLE_MEKANIK)
        m = Mekanik.objects.create(user=baru, status=Mekanik.STATUS_TERSEDIA)
        respons = self.ambil(reverse("kelola_mekanik"))
        self.assertContains(respons, f'action="{reverse("kelola_mekanik_hapus", args=[m.pk])}"')

    def test_riwayat_terakhir_mekanik_urutan_kolom_seperti_pelanggan(self):
        from servis.models import TransaksiServis
        t = TransaksiServis.objects.filter(status=TransaksiServis.STATUS_SELESAI, mekanik__isnull=False).first()
        self.client.force_login(t.mekanik.user)
        isi = self.client.get(reverse("mekanik_pengerjaan")).content.decode()
        riwayat = isi.split("Riwayat Terakhir", 1)[1]
        self.assertIn('class="tabel-data', riwayat)
        kolom = ["ID &amp; Tanggal", "Kendaraan", "Tipe Layanan", "Total Biaya", "Status", "Aksi"]
        posisi = [riwayat.index(f"<th>{k}</th>") for k in kolom]
        self.assertEqual(posisi, sorted(posisi))


class PenyesuaianLanjutan(TestCase):
    """Beli di kanan Hapus, judul gaya dasbor, alur Beli -> Batal, tampilan kosong."""

    def setUp(self):
        import io
        from django.core.management import call_command
        call_command("seed_demo", verbosity=0, stdout=io.StringIO(), izinkan_di_server=True)
        from sparepart.models import Sparepart
        self.sp = Sparepart.objects.order_by("pk").first()
        self.sp.stok = 0
        self.sp.save()
        self.client.force_login(User.objects.get(username="admin1"))

    def test_tombol_beli_di_kanan_ikon_hapus(self):
        isi = self.client.get(reverse("sparepart:sparepart_list")).content.decode()
        baris = isi.split(f'action="{reverse("sparepart:sparepart_delete", args=[self.sp.pk])}"', 1)[1]
        self.assertIn(f"?sparepart={self.sp.pk}", baris.split("</tr>", 1)[0])

    def test_judul_halaman_bergaya_dasbor_admin(self):
        for nama in ("sparepart:sparepart_list", "sparepart:peringatan_stok", "kelola_mekanik", "kelola_jenis"):
            with self.subTest(halaman=nama):
                self.assertContains(self.client.get(reverse(nama)), '<h1 class="h3 mb-1">')

    # Alur Beli -> Kembali/Batal (?next) diuji di pembelian/tests/test_views.py.

    def test_detail_servis_mekanik_punya_tombol_kembali_dan_navigasi_di_atas(self):
        from servis.models import TransaksiServis
        t = TransaksiServis.objects.filter(mekanik__isnull=False).first()
        self.client.force_login(t.mekanik.user)
        isi = self.client.get(reverse("mekanik_detail", args=[t.pk])).content.decode()
        self.assertIn(f'href="{reverse("mekanik_pengerjaan")}" class="tautan-kembali"', isi)
        samping = isi.split('class="dtl-samping"', 1)[1]
        self.assertLess(samping.index("<h3>Navigasi</h3>"), samping.index("<h3>Total Biaya</h3>"))

    def test_sidebar_admin_mengingat_posisi_gulir(self):
        isi = self.client.get(reverse("kelola_kasir")).content.decode()
        self.assertIn("js/sidebar.js", isi)

    def test_antrian_beranda_mekanik_memakai_tabel_bersama(self):
        from servis.models import TransaksiServis
        mek = User.objects.get(username="mekanik1")
        self.client.force_login(mek)
        isi = self.client.get(reverse("mekanik_dashboard")).content.decode()
        self.assertTrue(TransaksiServis.objects.filter(mekanik__isnull=True, status=TransaksiServis.STATUS_MENUNGGU).exists(),
                        "seed_demo harus punya antrian yang belum diambil")
        antrian = isi.split("Antrian Kendaraan", 1)[1]
        self.assertIn('class="tabel-data', antrian)
        kolom = ["ID &amp; Tanggal", "Kendaraan", "Tipe Layanan", "Status"]
        posisi = [antrian.index(f"<th>{k}</th>") for k in kolom]
        self.assertEqual(posisi, sorted(posisi))

    def test_tampilan_kosong_mekanik_seragam(self):
        from servis.models import TransaksiServis
        TransaksiServis.objects.all().delete()
        self.client.force_login(User.objects.get(username="mekanik1"))
        for nama in ("mekanik_antrian", "mekanik_home_service", "mekanik_pengerjaan", "mekanik_dashboard"):
            with self.subTest(halaman=nama):
                isi = self.client.get(reverse(nama)).content.decode()
                self.assertNotIn("kd-kosong", isi)
                self.assertRegex(isi, r'class="(hal-kosong|kosong)"')
