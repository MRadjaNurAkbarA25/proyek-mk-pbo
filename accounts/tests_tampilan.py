"""Penjaga kebersihan template.

Ketiga kelas di bawah ini lahir dari tiga bug yang sama-sama LOLOS dari
`manage.py check`, lolos dari seluruh tes lain, dan hanya ketahuan setelah
halamannya dibuka dengan mata:

1. Komentar pagar tiga baris tercetak utuh di kartu antrian mekanik.
2. Menu "Kinerja Mekanik" tampil tanpa ikon karena simbolnya ada di berkas
   yang tidak ikut dimuat.
3. Transaksi demo berstatus Selesai punya linimasa yang mulai di tengah.

Ketiganya diam: Django tidak menganggap satu pun sebagai error. Jadi yang
menjaganya harus tes, bukan check.
"""
import io
import re
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from servis.models import PembaruanServis, TransaksiServis

AKAR = Path(settings.BASE_DIR)


def semua_template():
    for p in sorted(AKAR.rglob("*.html")):
        if "__pycache__" in p.parts or "node_modules" in p.parts:
            continue
        yield p


class KomentarTemplate(TestCase):
    """Komentar pagar {# ... #} hanya berlaku satu baris.

    Dipakai untuk beberapa baris, Django tidak mengenalinya sebagai tag sama
    sekali dan mencetak isinya apa adanya ke halaman. Tidak ada error, tidak
    ada peringatan; pelanggan yang menemukannya.
    """

    def test_tidak_ada_komentar_pagar_lebih_dari_satu_baris(self):
        salah = []
        for p in semua_template():
            for n, baris in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if "{#" in baris and "#}" not in baris.split("{#", 1)[1]:
                    salah.append(f"{p.relative_to(AKAR)}:{n}")

        self.assertEqual(
            salah, [],
            "Komentar pagar yang dibuka tapi tidak ditutup di baris yang sama "
            "akan TERCETAK di halaman. Pakai {% comment %} ... {% endcomment %} "
            "untuk komentar lebih dari satu baris. Lokasi: " + ", ".join(salah),
        )


class IkonSidebar(TestCase):
    """Setiap <use href="#i-x"> harus punya <symbol id="i-x"> di halaman itu.

    SVG tidak mengeluh kalau simbol yang ditunjuk tidak ada: tag <use>-nya
    cuma menggambar kosong. Jadi menu yang ikonnya hilang tetap tampak
    "berfungsi" sampai ada yang memperhatikan ruang kosong di sebelah teks.
    """

    def setUp(self):
        call_command("seed_demo", verbosity=0, stdout=io.StringIO())

    def halaman(self, username, *url):
        self.client.force_login(User.objects.get(username=username))
        hasil = []
        for u in url:
            r = self.client.get(u)
            if r.status_code == 200:
                hasil.append((u, r.content.decode("utf-8", "ignore")))
        return hasil

    def periksa(self, username, *url):
        kurang = {}
        for u, html in self.halaman(username, *url):
            dipakai = set(re.findall(r'href="#(i-[a-z0-9-]+)"', html))
            ada = set(re.findall(r'id="(i-[a-z0-9-]+)"', html))
            if dipakai - ada:
                kurang[u] = sorted(dipakai - ada)
        self.assertEqual(
            kurang, {},
            "Ada <use> yang menunjuk simbol ikon yang tidak ikut dimuat di "
            "halaman itu. Simbolnya perlu disalin ke berkas ikon yang memang "
            "di-include kerangka halaman tersebut.",
        )

    def test_sidebar_admin(self):
        self.periksa("admin1", "/accounts/profil/", "/adminpanel/",
                     "/adminpanel/laporan/mekanik/", "/adminpanel/laporan/transaksi/")

    def test_sidebar_kasir(self):
        self.periksa("kasir1", "/accounts/profil/", "/kasir/", "/kasir/transaksi/")

    def test_sidebar_mekanik(self):
        self.periksa("mekanik1", "/accounts/profil/", "/mekanik/", "/sparepart/")

    def test_sidebar_pelanggan(self):
        self.periksa("pelanggan1", "/pelanggan/", "/pelanggan/riwayat/")


class DataDemoPunyaLinimasaUtuh(TestCase):
    """seed_demo harus menempuh alur asli, bukan memasang field langsung.

    Kalau mekaniknya dipasang lewat kwarg `mekanik=...`, ambil_oleh() tidak
    pernah dipanggil dan tahap Pemeriksaan tidak tercatat. Akibatnya saat
    demo ada servis berstatus Selesai yang riwayatnya baru mulai di
    "Persetujuan" — terlihat seperti fitur yang separuh jalan.
    """

    def setUp(self):
        call_command("seed_demo", verbosity=0, stdout=io.StringIO())

    def test_transaksi_selesai_punya_enam_tahap_berurutan(self):
        t = TransaksiServis.objects.filter(
            status=TransaksiServis.STATUS_SELESAI).first()
        self.assertIsNotNone(t, "seed_demo harus menyediakan satu transaksi Selesai")

        self.assertEqual(
            [p.tahap for p in t.pembaruan.all()],
            [
                PembaruanServis.TAHAP_PERMINTAAN,
                PembaruanServis.TAHAP_KEDATANGAN,
                PembaruanServis.TAHAP_PEMERIKSAAN,
                PembaruanServis.TAHAP_PERSETUJUAN,
                PembaruanServis.TAHAP_PERBAIKAN,
                PembaruanServis.TAHAP_SELESAI,
            ],
            "Transaksi demo yang sudah selesai harus punya cerita lengkap, "
            "supaya kartu Perkembangan Servis bisa dipakai saat demo.",
        )

    def test_tidak_ada_transaksi_demo_tanpa_linimasa(self):
        kosong = [t.kode_transaksi for t in TransaksiServis.objects.all()
                  if not t.pembaruan.exists()]
        self.assertEqual(kosong, [], "transaksi demo tanpa satu pun baris linimasa")

    def test_antrian_mekanik_tetap_terisi(self):
        """tandai_kendaraan_tiba() baru dipakai; antrian tidak boleh jadi kosong."""
        antri = TransaksiServis.objects.filter(
            status=TransaksiServis.STATUS_MENUNGGU,
            mekanik__isnull=True,
            kendaraan_hadir=True,
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
        )
        self.assertTrue(antri.exists(),
                        "harus tetap ada pekerjaan yang bisa diambil mekanik")
