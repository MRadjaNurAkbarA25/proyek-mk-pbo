"""FR-34: pencocokan kata kunci FAQ (skor_kecocokan dan cari).

Logikanya ada di model, bukan di JavaScript, justru supaya bisa diuji di sini.
"""
from django.test import SimpleTestCase, TestCase

from faq.models import KATA_UMUM, PertanyaanFAQ, kata_penting


def buat(pertanyaan, kata_kunci="", aktif=True, urutan=0, kategori=PertanyaanFAQ.KATEGORI_SERVIS):
    return PertanyaanFAQ.objects.create(
        kategori=kategori, pertanyaan=pertanyaan, jawaban="Jawaban " + pertanyaan,
        kata_kunci=kata_kunci, aktif=aktif, urutan=urutan,
    )


class KataPenting(SimpleTestCase):
    def test_kata_umum_dibuang(self):
        self.assertEqual(kata_penting("Apa saya bisa servis di bengkel dan ke rumah"), {"servis", "bengkel", "rumah"})

    def test_semua_kata_umum_dari_rancangan_terdaftar(self):
        self.assertEqual(KATA_UMUM, {"saya", "apa", "bagaimana", "cara", "yang", "di", "ke", "dan", "bisa"})

    def test_huruf_besar_dan_tanda_baca_tidak_berpengaruh(self):
        self.assertEqual(kata_penting("Servis REM?!"), {"servis", "rem"})

    def test_teks_kosong(self):
        self.assertEqual(kata_penting(""), set())
        self.assertEqual(kata_penting("   "), set())


class SkorKecocokan(TestCase):
    def test_skor_adalah_jumlah_kata_penting_yang_sama(self):
        f = buat("Berapa lama servis rem?", "durasi waktu")
        self.assertEqual(f.skor_kecocokan("berapa lama servis rem"), 4)
        self.assertEqual(f.skor_kecocokan("berapa lama"), 2)
        self.assertEqual(f.skor_kecocokan("durasi"), 1)

    def test_kata_kunci_ikut_dihitung(self):
        f = buat("Bagaimana cara mengajukan servis?", "service servise")
        self.assertEqual(f.skor_kecocokan("service"), 1)

    def test_kata_yang_sama_diketik_dua_kali_dihitung_sekali(self):
        f = buat("Servis rem", "")
        self.assertEqual(f.skor_kecocokan("rem rem rem"), 1)

    def test_kata_umum_tidak_menambah_skor(self):
        f = buat("Apa itu Home Service?", "")
        self.assertEqual(f.skor_kecocokan("apa saya bisa bagaimana cara"), 0)

    def test_tidak_ada_kata_sama_skor_nol(self):
        self.assertEqual(buat("Servis rem", "").skor_kecocokan("pembayaran transfer"), 0)


class Cari(TestCase):
    def test_pertanyaan_yang_lebih_cocok_naik_ke_atas(self):
        buat("Metode pembayaran apa saja?", "bayar transfer", urutan=1)
        rem = buat("Berapa lama servis rem?", "durasi waktu", urutan=2)
        buat("Bagaimana cara mengajukan servis?", "service", urutan=3)
        hasil = PertanyaanFAQ.cari("berapa lama servis rem")
        self.assertEqual(hasil[0], rem)          # skor 4, walau urutannya ke-2
        self.assertEqual(len(hasil), 2)           # yang lain: hanya "servis" cocok; pembayaran tidak

    def test_faq_nonaktif_tidak_muncul(self):
        buat("Berapa lama servis rem?", aktif=False)
        aktif = buat("Servis berkala", "rem")
        self.assertEqual(PertanyaanFAQ.cari("servis rem"), [aktif])

    def test_semua_nonaktif_hasilnya_kosong(self):
        buat("Berapa lama servis rem?", aktif=False)
        self.assertEqual(PertanyaanFAQ.cari("berapa lama servis rem"), [])

    def test_ketikan_tanpa_kata_penting_tidak_menghasilkan_apa_pun(self):
        buat("Apa itu Home Service?", "panggil rumah")
        for teks in ("", "   ", "apa saya bisa", "bagaimana cara yang di ke dan", "???"):
            with self.subTest(teks=teks):
                self.assertEqual(PertanyaanFAQ.cari(teks), [])

    def test_ketikan_tanpa_kecocokan_kosong(self):
        buat("Berapa lama servis rem?", "durasi")
        self.assertEqual(PertanyaanFAQ.cari("garansi aki"), [])

    def test_hanya_tiga_teratas(self):
        for i in range(5):
            buat(f"Servis jenis {i}", "", urutan=i)
        self.assertEqual(len(PertanyaanFAQ.cari("servis")), 3)

    def test_batas_bisa_diubah(self):
        for i in range(5):
            buat(f"Servis jenis {i}", "", urutan=i)
        self.assertEqual(len(PertanyaanFAQ.cari("servis", batas=1)), 1)

    def test_skor_sama_mengikuti_urutan_tampil(self):
        b = buat("Servis B", "", urutan=2)
        a = buat("Servis A", "", urutan=1)
        self.assertEqual(PertanyaanFAQ.cari("servis"), [a, b])

    def test_huruf_besar_dan_tanda_baca_pada_ketikan(self):
        rem = buat("Berapa lama servis rem?")
        self.assertEqual(PertanyaanFAQ.cari("BERAPA LAMA SERVIS REM???"), [rem])
