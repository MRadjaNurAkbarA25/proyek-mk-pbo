"""FR-34: pencocokan teks FAQ (faq/pencocokan.py) dan PertanyaanFAQ.cari().

Logikanya ada di Python, bukan di JavaScript, justru supaya bisa diuji di sini.
"""
from django.test import SimpleTestCase, TestCase

from faq import pencocokan as p
from faq.models import PertanyaanFAQ


def buat(pertanyaan, kata_kunci="", aktif=True, urutan=0, kategori=PertanyaanFAQ.KATEGORI_SERVIS):
    return PertanyaanFAQ.objects.create(
        kategori=kategori, pertanyaan=pertanyaan, jawaban="Jawaban " + pertanyaan,
        kata_kunci=kata_kunci, aktif=aktif, urutan=urutan,
    )


class Normalisasi(SimpleTestCase):
    def test_huruf_kecil_dan_tanpa_tanda_baca(self):
        self.assertEqual(p.normalisasi("Servis REM?!"), "servis rem")

    def test_teks_kosong(self):
        self.assertEqual(p.normalisasi(None), "")
        self.assertEqual(p.normalisasi("   "), "")

    def test_ejaan_gabungan_disatukan(self):
        for teks in ("e-wallet", "e wallet", "E-Wallet", "ewallet"):
            with self.subTest(teks=teks):
                self.assertEqual(p.normalisasi(teks), "ewallet")
        self.assertEqual(p.normalisasi("sign up"), "signup")
        for teks in ("no hp", "nomor hp", "no telp", "nomor telepon"):
            with self.subTest(teks=teks):
                self.assertEqual(p.normalisasi(teks), "nohp")


class Frasa(SimpleTestCase):
    def test_semua_ejaan_home_service_jadi_satu_token(self):
        for teks in ("home service", "homeservice", "home servis", "servis panggilan",
                     "servis ke rumah", "panggil mekanik", "mekanik datang"):
            with self.subTest(teks=teks):
                self.assertEqual(p.token(teks), ["home_service"])

    def test_kata_penyusun_frasa_tidak_ikut_dihitung(self):
        self.assertNotIn("servis", p.token("home service"))
        self.assertNotIn("mekanik", p.token("panggil mekanik"))

    def test_frasa_lain(self):
        for teks, harapan in (("kata sandi", "sandi"), ("password", "sandi"), ("pw", "sandi"),
                              ("nomor polisi", "nopol"), ("plat", "nopol"), ("nopol", "nopol"),
                              ("scan qr", "qris"), ("e money", "qris"), ("qris", "qris"),
                              ("daftar harga", "daftar_harga")):
            with self.subTest(teks=teks):
                self.assertEqual(p.token(teks), [harapan])

    def test_daftar_harga_tidak_sama_dengan_daftar_akun(self):
        self.assertNotIn("daftar", p.token("daftar harga"))
        self.assertIn("daftar", p.token("daftar akun"))


class Sinonim(SimpleTestCase):
    def test_ejaan_tidak_baku_jadi_kata_dasar(self):
        for kata, dasar in (("service", "servis"), ("servise", "servis"), ("serpis", "servis"),
                            ("srvis", "servis"), ("byr", "bayar"), ("cancel", "batal"),
                            ("brp", "berapa"), ("brapa", "berapa"), ("kpn", "kapan"),
                            ("gmn", "bagaimana"), ("gimana", "bagaimana"), ("bgmn", "bagaimana"),
                            ("mtr", "motor"), ("mbl", "mobil"), ("oil", "oli"),
                            ("account", "akun"), ("regis", "daftar"), ("register", "daftar"),
                            ("tf", "transfer")):
            with self.subTest(kata=kata):
                self.assertEqual(p.kata_dasar(kata), dasar)


class Stemming(SimpleTestCase):
    def test_contoh_nyata(self):
        for kata, dasar in (("membatalkan", "batal"), ("pembayaran", "bayar"), ("diservis", "servis"),
                            ("kendaraannya", "kendaraan"), ("dibatalkan", "batal"),
                            ("membayar", "bayar"), ("mendaftar", "daftar"), ("disetujui", "setuju")):
            with self.subTest(kata=kata):
                self.assertEqual(p.kata_dasar(kata), dasar)

    def test_kata_pendek_dan_nama_tidak_rusak(self):
        for kata in ("rem", "oli", "ban", "mekanik", "metode", "pesan", "menu", "budi", "dian", "beli"):
            with self.subTest(kata=kata):
                self.assertEqual(p.akar(kata), kata)

    def test_sisa_kurang_dari_empat_huruf_tidak_dipotong(self):
        self.assertEqual(p.akar("dian"), "dian")      # bukan di- + "an"
        self.assertEqual(p.akar("pesan"), "pesan")    # bukan pe- + "san"


class KataUmumDanKataTanya(SimpleTestCase):
    def test_kata_umum_dibuang(self):
        self.assertEqual(p.token("saya mau dong servis di bengkel ya kak"), ["servis", "bengkel"])

    def test_tidak_ada_kata_penting(self):
        for teks in ("", "apa saya bisa", "gak ga nggak tidak", "???"):
            with self.subTest(teks=teks):
                self.assertEqual(p.token(teks), [])

    def test_kata_tanya_disimpan(self):
        self.assertEqual(p.token("kapan bayar"), ["kapan", "bayar"])
        self.assertIn("berapa", p.token("brp biaya"))

    def test_berapa_lama_jadi_sinyal_durasi(self):
        self.assertIn("durasi", p.token("berapa lama servis"))
        self.assertNotIn("durasi", p.token("home service lama banget"))


class SalahKetik(SimpleTestCase):
    KOSAKATA = {"bayar", "diagnosis", "kendaraan", "servis", "rem"}

    def test_dicocokkan_ke_kata_terdekat(self):
        self.assertEqual(p.token("pembayran", self.KOSAKATA), ["bayar"])
        self.assertEqual(p.token("diagnosa", self.KOSAKATA), ["diagnosis"])
        self.assertEqual(p.token("kendaran", self.KOSAKATA), ["kendaraan"])

    def test_kata_pendek_tidak_dikoreksi(self):
        self.assertEqual(p.token("rme", self.KOSAKATA), ["rme"])

    def test_kata_acak_tidak_dipaksa_cocok(self):
        self.assertEqual(p.token("asdfgh", self.KOSAKATA), ["asdfgh"])


class Skor(SimpleTestCase):
    DOKUMEN = [
        ("Berapa lama servis rem?", "durasi"),
        ("Bagaimana cara mengajukan servis?", "ajukan"),
        ("Apa itu Home Service?", "panggil rumah"),
    ]

    def test_kata_langka_lebih_menentukan(self):
        skor = p.nilai("servis rem", self.DOKUMEN)
        self.assertGreater(skor[0], skor[1])

    def test_pertanyaan_lebih_berat_dari_kata_kunci(self):
        skor = p.nilai("durasi", [("Durasi servis", ""), ("Lain", "durasi")])
        self.assertGreater(skor[0], skor[1])

    def test_home_service_tidak_menambah_skor_servis_bengkel(self):
        self.assertEqual(p.nilai("home service", self.DOKUMEN)[1], 0)

    def test_tanpa_kecocokan_nol(self):
        self.assertEqual(p.nilai("pembayaran transfer", self.DOKUMEN), [0, 0, 0])


class Cari(TestCase):
    def test_pertanyaan_yang_lebih_cocok_naik_ke_atas(self):
        buat("Metode pembayaran apa saja?", "bayar transfer", urutan=1)
        rem = buat("Berapa lama servis rem?", "durasi waktu", urutan=2)
        buat("Bagaimana cara mengajukan servis?", "service", urutan=3)
        self.assertEqual(PertanyaanFAQ.cari("berapa lama servis rem")[0], rem)

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


class Yakin(TestCase):
    def test_satu_jawaban_jelas_unggul(self):
        buat("Berapa lama servis rem?", "durasi")
        buat("Apa itu Home Service?", "panggil rumah")
        hasil, yakin = PertanyaanFAQ.cari_lengkap("berapa lama servis rem")
        self.assertTrue(yakin)
        self.assertEqual(hasil[0][0].pertanyaan, "Berapa lama servis rem?")

    def test_skor_berimbang_tidak_yakin(self):
        buat("Servis A")
        buat("Servis B")
        hasil, yakin = PertanyaanFAQ.cari_lengkap("servis")
        self.assertEqual(len(hasil), 2)
        self.assertFalse(yakin)

    def test_tanpa_hasil_tidak_yakin(self):
        buat("Servis A")
        self.assertEqual(PertanyaanFAQ.cari_lengkap("garansi aki"), ([], False))
