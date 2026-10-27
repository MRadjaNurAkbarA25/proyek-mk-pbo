"""FR-34: endpoint chat dan tempat gelembung chat dipasang."""
from django.core.management import call_command
from django.test import TestCase
from io import StringIO

from accounts.models import Mekanik, Pelanggan, User
from faq.models import PertanyaanFAQ

S, H = PertanyaanFAQ.KATEGORI_SERVIS, PertanyaanFAQ.KATEGORI_HOME_SERVICE


def buat(pertanyaan, kategori=S, aktif=True, kata_kunci="", urutan=0):
    return PertanyaanFAQ.objects.create(
        kategori=kategori, pertanyaan=pertanyaan, jawaban="Jawaban: " + pertanyaan,
        kata_kunci=kata_kunci, aktif=aktif, urutan=urutan)


class EndpointDaftar(TestCase):
    def test_pengunjung_belum_login_bisa_membuka(self):
        buat("Servis rem")
        respons = self.client.get("/faq/daftar/")
        self.assertEqual(respons.status_code, 200)
        self.assertEqual(respons["Content-Type"], "application/json")

    def test_isinya_kategori_berisi_pertanyaan_dan_jawaban(self):
        f = buat("Servis rem")
        data = self.client.get("/faq/daftar/").json()
        self.assertEqual(data["kategori"], [{
            "kode": S, "nama": "Servis di Bengkel",
            "pertanyaan": [{"id": f.pk, "pertanyaan": "Servis rem", "jawaban": "Jawaban: Servis rem"}],
        }])

    def test_kategori_mengikuti_urutan_rancangan_dan_pertanyaan_mengikuti_urutan(self):
        buat("HS", kategori=H)
        buat("B", urutan=2)
        buat("A", urutan=1)
        data = self.client.get("/faq/daftar/").json()["kategori"]
        self.assertEqual([k["kode"] for k in data], [S, H])
        self.assertEqual([p["pertanyaan"] for p in data[0]["pertanyaan"]], ["A", "B"])

    def test_faq_nonaktif_dan_kategori_kosong_tidak_tampil(self):
        buat("Nonaktif", kategori=H, aktif=False)
        buat("Aktif")
        data = self.client.get("/faq/daftar/").json()["kategori"]
        self.assertEqual([k["kode"] for k in data], [S])

    def test_kata_kunci_tidak_dibocorkan(self):
        buat("Servis rem", kata_kunci="rahasia-internal")
        self.assertNotIn("rahasia-internal", self.client.get("/faq/daftar/").content.decode())

    def test_jawaban_yang_diubah_langsung_terlihat(self):
        f = buat("Servis rem")
        self.client.get("/faq/daftar/")
        f.jawaban = "Jawaban baru"
        f.save()
        self.assertIn("Jawaban baru", self.client.get("/faq/daftar/").content.decode())

    def test_hanya_get(self):
        self.assertEqual(self.client.post("/faq/daftar/").status_code, 405)

    def test_tidak_boleh_disimpan_cache(self):
        self.assertIn("no-store", self.client.get("/faq/daftar/")["Cache-Control"])


class EndpointCari(TestCase):
    def test_mengetik_berapa_lama_servis_rem_mendapat_faq_yang_relevan(self):
        """Kriteria selesai FR-34, dengan FAQ awal dari seed_demo."""
        call_command("seed_demo", izinkan_di_server=True, stdout=StringIO())
        hasil = self.client.get("/faq/cari/", {"q": "berapa lama servis rem"}).json()["hasil"]
        self.assertGreaterEqual(len(hasil), 1)
        self.assertLessEqual(len(hasil), 3)
        self.assertEqual(hasil[0]["pertanyaan"], "Berapa lama waktu pengerjaan servis?")
        self.assertIn("rem", hasil[0]["jawaban"].lower())

    def test_pengunjung_belum_login_bisa_mencari(self):
        buat("Servis rem")
        self.assertEqual(self.client.get("/faq/cari/", {"q": "rem"}).status_code, 200)

    def test_tidak_ada_yang_cocok_hasil_kosong(self):
        buat("Servis rem")
        self.assertEqual(self.client.get("/faq/cari/", {"q": "garansi aki"}).json()["hasil"], [])

    def test_ketikan_hanya_kata_umum_hasil_kosong(self):
        buat("Apa itu Home Service?")
        self.assertEqual(self.client.get("/faq/cari/", {"q": "apa saya bisa"}).json()["hasil"], [])

    def test_tanpa_parameter_q_hasil_kosong(self):
        buat("Servis rem")
        self.assertEqual(self.client.get("/faq/cari/").json(), {"hasil": [], "yakin": False, "jenis": "cari"})

    def test_faq_nonaktif_tidak_dikembalikan(self):
        buat("Servis rem", aktif=False)
        self.assertEqual(self.client.get("/faq/cari/", {"q": "servis rem"}).json()["hasil"], [])

    def test_paling_banyak_tiga(self):
        for i in range(6):
            buat(f"Servis {i}")
        self.assertEqual(len(self.client.get("/faq/cari/", {"q": "servis"}).json()["hasil"]), 3)

    def test_ketikan_sangat_panjang_tidak_error(self):
        buat("Servis rem")
        self.assertEqual(self.client.get("/faq/cari/", {"q": "rem " * 5000}).status_code, 200)

    def test_hanya_get(self):
        self.assertEqual(self.client.post("/faq/cari/", {"q": "rem"}).status_code, 405)

    def test_tidak_ada_yang_tersimpan(self):
        """Riwayat percakapan tidak disimpan: mengetik tidak mengubah database
        dan tidak membuat sesi."""
        buat("Servis rem")
        respons = self.client.get("/faq/cari/", {"q": "servis rem"})
        self.assertEqual(PertanyaanFAQ.objects.count(), 1)
        self.assertNotIn("sessionid", respons.cookies)


class JenisDanYakin(TestCase):
    """Field tambahan /faq/cari/: yakin (jawaban teratas jelas unggul) dan jenis."""

    def test_satu_jawaban_jelas_unggul_yakin(self):
        buat("Berapa lama servis rem?", kata_kunci="durasi")
        buat("Apa itu Home Service?", kategori=H, kata_kunci="panggil rumah")
        data = self.client.get("/faq/cari/", {"q": "berapa lama servis rem"}).json()
        self.assertEqual((data["jenis"], data["yakin"]), ("cari", True))
        self.assertEqual(data["hasil"][0]["pertanyaan"], "Berapa lama servis rem?")

    def test_skor_berimbang_tidak_yakin(self):
        buat("Servis A")
        buat("Servis B")
        data = self.client.get("/faq/cari/", {"q": "servis"}).json()
        self.assertEqual(len(data["hasil"]), 2)
        self.assertFalse(data["yakin"])

    def test_sapaan_dikenali_di_server(self):
        buat("Servis rem")
        for q in ("halo", "Selamat pagi", "permisi kak"):
            with self.subTest(q=q):
                self.assertEqual(self.client.get("/faq/cari/", {"q": q}).json(),
                                 {"hasil": [], "yakin": False, "jenis": "sapaan"})

    def test_terima_kasih_dikenali_di_server(self):
        for q in ("makasih", "terima kasih ya", "thanks"):
            with self.subTest(q=q):
                self.assertEqual(self.client.get("/faq/cari/", {"q": q}).json()["jenis"], "terima_kasih")


class TempatGelembung(TestCase):
    """Landing dan halaman pelanggan: ada. Kasir, mekanik, admin: tidak ada."""
    PENANDA = 'id="faq-chat"'

    def _login(self, role):
        user = User.objects.create_user(username=f"u_{role}", password="x", role=role)
        if role == User.ROLE_PELANGGAN:
            Pelanggan.objects.create(user=user)
        if role == User.ROLE_MEKANIK:
            Mekanik.objects.create(user=user)
        self.client.force_login(user)

    def test_landing_untuk_pengunjung_belum_login(self):
        respons = self.client.get("/")
        self.assertContains(respons, self.PENANDA)
        self.assertContains(respons, "js/faq.js")
        self.assertContains(respons, "css/faq.css")

    def test_landing_membawa_nomor_whatsapp_bengkel(self):
        # +62 895-0320-2323 -> 628950320 2323 (angka internasional)
        self.assertContains(self.client.get("/"), 'data-wa="62895')

    def test_halaman_pelanggan(self):
        self._login(User.ROLE_PELANGGAN)
        for url in ("/pelanggan/dashboard/", "/pelanggan/kendaraan/", "/pelanggan/ajukan-servis/",
                    "/pelanggan/home-service/pesan/", "/pelanggan/riwayat/", "/accounts/profil/"):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), self.PENANDA)

    def test_tidak_ada_di_halaman_admin(self):
        self._login(User.ROLE_ADMIN)
        for url in ("/adminpanel/dashboard/", "/adminpanel/faq/", "/adminpanel/kasir/"):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), self.PENANDA)

    def test_tidak_ada_di_halaman_kasir(self):
        self._login(User.ROLE_KASIR)
        self.assertNotContains(self.client.get("/kasir/dashboard/"), self.PENANDA)

    def test_tidak_ada_di_halaman_mekanik(self):
        self._login(User.ROLE_MEKANIK)
        self.assertNotContains(self.client.get("/mekanik/dashboard/"), self.PENANDA)
