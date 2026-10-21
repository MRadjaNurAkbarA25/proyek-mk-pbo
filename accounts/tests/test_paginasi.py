"""Uji paginasi semua daftar panjang.

Yang penting dijaga di sini: halaman kedua benar-benar berisi data yang beda,
?page= yang ngawur tidak membuat error 500, dan filter pencarian tidak hilang
saat pindah halaman (ini bug paling mudah terjadi pada paginasi).
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Mekanik, Pelanggan, User
from bengkel_project.paginasi import PER_HALAMAN_PADAT, PER_HALAMAN_TABEL
from kendaraan.models import Motor
from servis.models import TransaksiServis
from sparepart.models import Sparepart

SANDI = "rahasia12345"


class PaginasiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="adm", password=SANDI, role=User.ROLE_ADMIN
        )
        cls.kasir = User.objects.create_user(
            username="kas", password=SANDI, role=User.ROLE_KASIR
        )
        user_pel = User.objects.create_user(
            username="pel", password=SANDI, role=User.ROLE_PELANGGAN
        )
        cls.pelanggan = Pelanggan.objects.create(user=user_pel)
        user_mek = User.objects.create_user(
            username="mek", password=SANDI, role=User.ROLE_MEKANIK
        )
        Mekanik.objects.create(user=user_mek)

        # Lebih dari satu halaman untuk tiap daftar.
        jumlah = PER_HALAMAN_TABEL + 5
        for i in range(jumlah):
            kendaraan = Motor.objects.create(
                pelanggan=cls.pelanggan, no_polisi=f"KT {100 + i} UJ",
                merk="Honda", model_kendaraan=f"Beat {i}", tahun=2021,
                jenis_motor="Matic", kapasitas_mesin=110,
            )
            TransaksiServis.objects.create(
                pelanggan=cls.pelanggan, kendaraan=kendaraan,
                keluhan=f"Keluhan uji {i}",
                tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
            )
            u = User.objects.create_user(
                username=f"pel_uji{i}", password=SANDI,
                role=User.ROLE_PELANGGAN, first_name=f"Pelanggan Uji {i}",
            )
            Pelanggan.objects.create(user=u)
            um = User.objects.create_user(
                username=f"mek_uji{i}", password=SANDI, role=User.ROLE_MEKANIK
            )
            Mekanik.objects.create(user=um)

        # Daftar sparepart memakai batas berbeda (PER_HALAMAN_PADAT), jadi
        # jumlah barisnya ikut disesuaikan supaya tetap lebih dari satu halaman.
        for i in range(PER_HALAMAN_PADAT + 5):
            Sparepart.objects.create(
                kode=f"UJI-{i:03d}", nama=f"Sparepart Uji {i:03d}", kategori="Oli",
                harga=50000, stok=20, stok_minimum=5,
            )

    # (nama url, username yang berhak)
    HALAMAN = [
        ("kasir_transaksi_daftar", "kas"),
        ("kelola_pelanggan", "adm"),
        ("kelola_mekanik", "adm"),
        ("sparepart:sparepart_list", "adm"),
        ("mekanik_antrian", "mek"),
        ("riwayat_service", "pel"),
    ]

    def test_halaman_pertama_dan_kedua_terbuka(self):
        for nama_url, username in self.HALAMAN:
            with self.subTest(halaman=nama_url):
                self.client.login(username=username, password=SANDI)
                url = reverse(nama_url)
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.get(url + "?page=2").status_code, 200)

    def test_navigasi_halaman_muncul(self):
        for nama_url, username in self.HALAMAN:
            with self.subTest(halaman=nama_url):
                self.client.login(username=username, password=SANDI)
                isi = self.client.get(reverse(nama_url)).content.decode()
                self.assertIn("Navigasi halaman", isi)
                self.assertIn("Berikutnya", isi)

    def test_page_ngawur_tidak_error(self):
        """?page=abc dan ?page=999 harus jatuh ke halaman valid, bukan 404/500."""
        for nama_url, username in self.HALAMAN:
            with self.subTest(halaman=nama_url):
                self.client.login(username=username, password=SANDI)
                url = reverse(nama_url)
                for parameter in ("?page=abc", "?page=999", "?page=0", "?page=-1"):
                    self.assertEqual(
                        self.client.get(url + parameter).status_code, 200,
                        f"{url}{parameter} seharusnya tetap 200",
                    )

    def test_halaman_kedua_berisi_baris_yang_berbeda(self):
        self.client.login(username="adm", password=SANDI)
        url = reverse("sparepart:sparepart_list")
        satu = self.client.get(url).context["halaman"]
        dua = self.client.get(url + "?page=2").context["halaman"]
        self.assertEqual(satu.number, 1)
        self.assertEqual(dua.number, 2)
        kode_satu = {s.kode for s in satu.object_list}
        kode_dua = {s.kode for s in dua.object_list}
        self.assertTrue(kode_satu)
        self.assertTrue(kode_dua)
        self.assertFalse(kode_satu & kode_dua, "halaman 1 dan 2 tidak boleh beririsan")

    def test_jumlah_baris_per_halaman_dipatuhi(self):
        self.client.login(username="adm", password=SANDI)
        halaman = self.client.get(reverse("kelola_pelanggan")).context["halaman"]
        self.assertEqual(len(halaman.object_list), PER_HALAMAN_TABEL)

    def test_filter_ikut_terbawa_ke_tautan_halaman(self):
        """Tautan halaman harus menyimpan parameter pencarian yang sedang aktif."""
        self.client.login(username="adm", password=SANDI)
        isi = self.client.get(
            reverse("kelola_pelanggan") + "?q=Pelanggan+Uji"
        ).content.decode()
        self.assertIn("q=Pelanggan", isi)
        self.assertIn("page=2", isi)
        # Pastikan keduanya ada pada satu tautan yang sama, bukan terpisah.
        self.assertRegex(isi, r'href="\?[^"]*q=Pelanggan[^"]*page=2')

    def test_filter_status_kasir_ikut_terbawa(self):
        self.client.login(username="kas", password=SANDI)
        isi = self.client.get(
            reverse("kasir_transaksi_daftar") + "?status=MENUNGGU"
        ).content.decode()
        self.assertRegex(isi, r'href="\?[^"]*status=MENUNGGU[^"]*page=2')

    def test_jumlah_total_tetap_dihitung_dari_semua_data(self):
        """Angka 'ditemukan' harus total seluruh data, bukan isi satu halaman."""
        self.client.login(username="kas", password=SANDI)
        respons = self.client.get(reverse("kasir_transaksi_daftar"))
        self.assertEqual(
            respons.context["jumlah_hasil"], TransaksiServis.objects.count()
        )
