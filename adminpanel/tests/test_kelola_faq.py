"""FR-34: Kelola FAQ untuk admin. Tambah, ubah, nonaktifkan; tidak ada hapus.

Kriteria selesai: admin bisa mengubah jawaban tanpa menyentuh kode.
"""
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from accounts.models import Pelanggan, User
from faq.models import PertanyaanFAQ

S = PertanyaanFAQ.KATEGORI_SERVIS


def data_form(**ganti):
    data = {"kategori": S, "pertanyaan": "Apakah bengkel buka hari Minggu?",
            "jawaban": "Buka, pukul 10.00 sampai 16.00.", "kata_kunci": "buka minggu jam",
            "urutan": 5, "aktif": "on"}
    data.update(ganti)
    return data


class DasarFAQ(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin9", password="x", role=User.ROLE_ADMIN)
        self.faq = PertanyaanFAQ.objects.create(
            kategori=S, pertanyaan="Berapa lama servis rem?", jawaban="Sekitar 1 jam.",
            kata_kunci="durasi", urutan=1)
        self.client.force_login(self.admin)


class AksesFAQ(DasarFAQ):
    URL = ["/adminpanel/faq/", "/adminpanel/faq/tambah/", "/adminpanel/faq/1/ubah/"]

    def test_pengunjung_belum_login_diarahkan_ke_login(self):
        self.client.logout()
        for url in self.URL:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse("login"))

    def test_role_lain_ditolak(self):
        for role in (User.ROLE_PELANGGAN, User.ROLE_KASIR, User.ROLE_MEKANIK):
            user = User.objects.create_user(username=f"x_{role}", password="x", role=role)
            if role == User.ROLE_PELANGGAN:
                Pelanggan.objects.create(user=user)
            self.client.force_login(user)
            for url in self.URL:
                with self.subTest(role=role, url=url):
                    self.assertEqual(self.client.get(url).status_code, 302)
            self.assertEqual(self.client.post(f"/adminpanel/faq/{self.faq.pk}/status/", {"aktif": "0"}).status_code, 302)
            self.faq.refresh_from_db()
            self.assertTrue(self.faq.aktif)

    def test_menu_kelola_faq_ada_di_sidebar_admin(self):
        self.assertContains(self.client.get("/adminpanel/dashboard/"), "Kelola FAQ")


class DaftarFAQ(DasarFAQ):
    def test_daftar_menampilkan_aktif_dan_nonaktif(self):
        PertanyaanFAQ.objects.create(kategori=S, pertanyaan="FAQ lama", jawaban="x", aktif=False)
        respons = self.client.get("/adminpanel/faq/")
        self.assertContains(respons, "Berapa lama servis rem?")
        self.assertContains(respons, "FAQ lama")
        self.assertContains(respons, "Nonaktif")

    def test_nonaktif_diurutkan_di_bawah(self):
        PertanyaanFAQ.objects.create(kategori=S, pertanyaan="FAQ lama", jawaban="x", aktif=False, urutan=0)
        urutan = [f.pertanyaan for f in self.client.get("/adminpanel/faq/").context["daftar"]]
        self.assertEqual(urutan, ["Berapa lama servis rem?", "FAQ lama"])

    def test_filter_kategori_dan_pencarian(self):
        PertanyaanFAQ.objects.create(kategori=PertanyaanFAQ.KATEGORI_AKUN, pertanyaan="Lupa sandi?", jawaban="x")
        respons = self.client.get("/adminpanel/faq/", {"kategori": PertanyaanFAQ.KATEGORI_AKUN})
        self.assertEqual([f.pertanyaan for f in respons.context["daftar"]], ["Lupa sandi?"])
        respons = self.client.get("/adminpanel/faq/", {"q": "durasi"})   # cocok lewat kata kunci
        self.assertEqual([f.pk for f in respons.context["daftar"]], [self.faq.pk])

    def test_kategori_asal_diabaikan(self):
        self.assertEqual(self.client.get("/adminpanel/faq/", {"kategori": "NGAWUR"}).status_code, 200)


class TambahUbahFAQ(DasarFAQ):
    def test_tambah(self):
        respons = self.client.post("/adminpanel/faq/tambah/", data_form())
        self.assertRedirects(respons, "/adminpanel/faq/")
        baru = PertanyaanFAQ.objects.get(pertanyaan="Apakah bengkel buka hari Minggu?")
        self.assertTrue(baru.aktif)
        self.assertEqual(baru.urutan, 5)

    def test_faq_baru_langsung_bisa_dicari_di_chat(self):
        self.client.post("/adminpanel/faq/tambah/", data_form())
        hasil = self.client.get("/faq/cari/", {"q": "jam buka minggu"}).json()["hasil"]
        self.assertEqual(hasil[0]["pertanyaan"], "Apakah bengkel buka hari Minggu?")

    def test_admin_mengubah_jawaban_dan_chat_langsung_berubah(self):
        """Kriteria selesai: ubah jawaban tanpa menyentuh kode."""
        respons = self.client.post(f"/adminpanel/faq/{self.faq.pk}/ubah/", data_form(
            pertanyaan=self.faq.pertanyaan, jawaban="Sekarang cukup 45 menit.", kata_kunci="durasi"))
        self.assertRedirects(respons, "/adminpanel/faq/")
        self.faq.refresh_from_db()
        self.assertEqual(self.faq.jawaban, "Sekarang cukup 45 menit.")
        chat = self.client.get("/faq/daftar/").json()
        self.assertEqual(chat["kategori"][0]["pertanyaan"][0]["jawaban"], "Sekarang cukup 45 menit.")

    def test_menu_ubah_menampilkan_isi_lama(self):
        self.assertContains(self.client.get(f"/adminpanel/faq/{self.faq.pk}/ubah/"), "Sekitar 1 jam.")

    def test_ubah_faq_yang_tidak_ada_404(self):
        self.assertEqual(self.client.get("/adminpanel/faq/9999/ubah/").status_code, 404)

    def test_pertanyaan_dan_jawaban_wajib(self):
        for kolom in ("pertanyaan", "jawaban"):
            with self.subTest(kolom=kolom):
                respons = self.client.post("/adminpanel/faq/tambah/", data_form(**{kolom: "   "}))
                self.assertEqual(respons.status_code, 200)
                self.assertTrue(respons.context["form"].errors[kolom])
        self.assertEqual(PertanyaanFAQ.objects.count(), 1)

    def test_kategori_harus_salah_satu_dari_empat(self):
        respons = self.client.post("/adminpanel/faq/tambah/", data_form(kategori="LAIN"))
        self.assertTrue(respons.context["form"].errors["kategori"])

    def test_kata_kunci_dirapikan_dan_boleh_kosong(self):
        self.client.post("/adminpanel/faq/tambah/", data_form(kata_kunci="  servis    service  "))
        self.assertEqual(PertanyaanFAQ.objects.get(urutan=5).kata_kunci, "servis service")
        self.client.post("/adminpanel/faq/tambah/", data_form(pertanyaan="Lain", kata_kunci=""))
        self.assertEqual(PertanyaanFAQ.objects.get(pertanyaan="Lain").kata_kunci, "")

    def test_urutan_negatif_ditolak(self):
        respons = self.client.post("/adminpanel/faq/tambah/", data_form(urutan=-1))
        self.assertTrue(respons.context["form"].errors["urutan"])


class NonaktifkanFAQ(DasarFAQ):
    def _status(self, aktif, **tambahan):
        return self.client.post(f"/adminpanel/faq/{self.faq.pk}/status/", {"aktif": aktif, **tambahan})

    def test_nonaktifkan_menyembunyikan_dari_chat_tapi_tidak_menghapus(self):
        self._status("0")
        self.faq.refresh_from_db()
        self.assertFalse(self.faq.aktif)
        self.assertEqual(PertanyaanFAQ.objects.count(), 1)
        self.assertEqual(self.client.get("/faq/daftar/").json(), {"kategori": []})
        self.assertEqual(self.client.get("/faq/cari/", {"q": "servis rem"}).json(), {"hasil": []})

    def test_aktifkan_kembali(self):
        self.faq.nonaktifkan()
        self._status("1")
        self.faq.refresh_from_db()
        self.assertTrue(self.faq.aktif)
        self.assertEqual(len(self.client.get("/faq/cari/", {"q": "servis rem"}).json()["hasil"]), 1)

    def test_hanya_post(self):
        self.assertEqual(self.client.get(f"/adminpanel/faq/{self.faq.pk}/status/").status_code, 405)

    def test_kembali_ke_halaman_asal_yang_aman(self):
        self.assertRedirects(self._status("0", next="/adminpanel/faq/?kategori=SERVIS"),
                             "/adminpanel/faq/?kategori=SERVIS")

    def test_tujuan_di_luar_situs_diabaikan(self):
        self.assertRedirects(self._status("1", next="https://jahat.example/"), "/adminpanel/faq/")

    def test_tidak_ada_jalur_hapus(self):
        with self.assertRaises(NoReverseMatch):
            reverse("kelola_faq_hapus", args=[self.faq.pk])
        self.assertEqual(self.client.post(f"/adminpanel/faq/{self.faq.pk}/hapus/").status_code, 404)
        self.assertEqual(PertanyaanFAQ.objects.count(), 1)

    def test_django_admin_juga_tidak_boleh_menghapus(self):
        from django.contrib import admin
        from django.test import RequestFactory

        izin = admin.site._registry[PertanyaanFAQ].has_delete_permission(RequestFactory().get("/"))
        self.assertFalse(izin)
