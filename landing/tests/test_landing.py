"""Landing page: isi fitur nyata, angka dari database, ajakan sesuai status login."""
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from landing.views import statistik_bengkel
from mekanik.models import JenisServis


class Statistik(TestCase):
    def test_angka_nol_tidak_ditampilkan(self):
        self.assertEqual(statistik_bengkel(), [])

    def test_angka_dari_database(self):
        JenisServis.objects.create(nama_servis="Ganti Oli", harga=50000, estimasi_waktu=30)
        u = User.objects.create_user(username="m", password="x", role=User.ROLE_MEKANIK)
        Mekanik.objects.create(user=u)
        nonaktif = User.objects.create_user(username="m2", password="x", role=User.ROLE_MEKANIK, is_active=False)
        Mekanik.objects.create(user=nonaktif)
        angka = {s["label"]: s["angka"] for s in statistik_bengkel()}
        self.assertEqual(angka, {"Jenis layanan": 1, "Mekanik aktif": 1})

    def test_tiap_statistik_punya_ikon(self):
        JenisServis.objects.create(nama_servis="Ganti Oli", harga=50000, estimasi_waktu=30)
        u = User.objects.create_user(username="m", password="x", role=User.ROLE_MEKANIK)
        Mekanik.objects.create(user=u)
        p = User.objects.create_user(username="p", password="x", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=p)
        statistik = statistik_bengkel()
        self.assertEqual(len(statistik), 3)
        for s in statistik:
            self.assertTrue(s["ikon"].startswith("i-"), s)

        # Ikon tampil di kartu dan simbolnya ikut dimuat di halaman.
        html = self.client.get("/").content.decode()
        for s in statistik:
            self.assertIn(f'<use href="#{s["ikon"]}"></use>', html)
            self.assertIn(f'<symbol id="{s["ikon"]}"', html)


class Halaman(TestCase):
    def test_menu_atas_berbahasa_indonesia(self):
        html = self.client.get("/").content.decode()
        menu = html[html.index('<header class="nav">'):html.index("</header>")]
        for teks in ("Beranda", "Tentang", "Layanan", "Cara Kerja", "Kontak", "Login", "Sign Up"):
            self.assertIn(f">{teks}</a>", menu)
        for teks in ("Home", "About", "Service", "Contact"):
            self.assertNotIn(f">{teks}</a>", menu)
        for anchor in ("#home", "#about", "#layanan", "#contact"):
            self.assertIn(f'href="{anchor}"', menu)

    def test_tombol_dasbor_untuk_yang_sudah_login(self):
        u = User.objects.create_user(username="p", password="x", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=u)
        self.client.force_login(u)
        html = self.client.get("/").content.decode()
        menu = html[html.index('<header class="nav">'):html.index("</header>")]
        self.assertIn(">Dasbor</a>", menu)
        self.assertNotIn("Dashboard", menu)

    def test_pengunjung_diajak_mendaftar(self):
        r = self.client.get("/")
        self.assertContains(r, "Daftar dan Ajukan Servis")
        self.assertContains(r, 'href="/accounts/register/" class="chip-jenis"', count=2)
        self.assertContains(r, "Cara Kerja")
        self.assertContains(r, "https://wa.me/62")
        self.assertNotContains(r, 'id="harga"')  # belum ada jenis servis

    def test_pelanggan_langsung_ke_halaman_pelanggan(self):
        u = User.objects.create_user(username="p", password="x", role=User.ROLE_PELANGGAN)
        Pelanggan.objects.create(user=u)
        self.client.force_login(u)
        r = self.client.get("/")
        self.assertContains(r, 'href="/pelanggan/ajukan-servis/"')
        self.assertContains(r, 'href="/pelanggan/kendaraan/tambah/motor/"')
        self.assertNotContains(r, "Daftar dan Ajukan Servis")

    def test_judul_alasan_di_atas_daftar_poin(self):
        # Masukan dosen: judul dan subjudul berada di kolom kanan, di atas
        # daftar poin, bukan di atas gambar.
        html = self.client.get("/").content.decode()
        gambar = html.index('class="img-frame img-alasan"')
        judul = html.index("Alasan Memilih Kami</h2>")
        daftar = html.index('class="alasan-list"')
        self.assertLess(gambar, judul)
        self.assertLess(judul, daftar)

    def test_daftar_harga_maks_enam(self):
        for i in range(8):
            JenisServis.objects.create(nama_servis=f"Layanan {i}", harga=10000 * (i + 1), estimasi_waktu=30)
        r = self.client.get("/")
        self.assertContains(r, 'class="harga-kartu"', count=6)
        self.assertContains(r, "Rp 10.000")
        self.assertContains(r, "Dan 2 layanan lainnya.")
        self.assertNotContains(r, "Layanan 7<")
