"""FR-34: isi awal FAQ lewat seed_demo, pembaruan teks lama, dan placeholder Info Bengkel."""
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from faq.data_awal import FAQ_AWAL, VERSI_LAMA, isi_faq_awal
from faq.models import PertanyaanFAQ, isi_placeholder
from faq.pencocokan import token
from landing.context_processors import info_bengkel


class IsiAwal(TestCase):
    def test_empat_puluh_sampai_lima_puluh_faq_dan_semua_kategori_terisi(self):
        self.assertEqual(isi_faq_awal(), len(FAQ_AWAL))
        self.assertTrue(40 <= PertanyaanFAQ.objects.count() <= 50)
        kode_kategori = {kode for kode, _ in PertanyaanFAQ.KATEGORI_CHOICES}
        self.assertEqual(set(PertanyaanFAQ.objects.values_list("kategori", flat=True)), kode_kategori)

    def test_semua_lengkap_dan_aktif(self):
        isi_faq_awal()
        for f in PertanyaanFAQ.objects.all():
            self.assertTrue(f.aktif)
            self.assertTrue(f.jawaban.strip(), f.pertanyaan)
            self.assertTrue(f.kata_kunci.strip(), f.pertanyaan)

    def test_pertanyaan_tidak_ada_yang_dobel(self):
        semua = [p for _, p, _, _ in FAQ_AWAL]
        self.assertEqual(len(semua), len(set(semua)))

    def test_aman_dijalankan_berulang(self):
        isi_faq_awal()
        self.assertEqual(isi_faq_awal(), 0)
        self.assertEqual(PertanyaanFAQ.objects.count(), len(FAQ_AWAL))

    def test_tidak_menimpa_jawaban_yang_sudah_diubah_admin(self):
        isi_faq_awal()
        f = PertanyaanFAQ.objects.get(pertanyaan="Metode pembayaran apa saja yang tersedia?")
        f.jawaban = "Jawaban buatan admin"
        f.aktif = False
        f.save()
        isi_faq_awal()
        f.refresh_from_db()
        self.assertEqual(f.jawaban, "Jawaban buatan admin")
        self.assertFalse(f.aktif)

    def test_seed_demo_mengisi_faq(self):
        call_command("seed_demo", izinkan_di_server=True, stdout=StringIO())
        self.assertEqual(PertanyaanFAQ.objects.count(), len(FAQ_AWAL))
        call_command("seed_demo", izinkan_di_server=True, stdout=StringIO())
        self.assertEqual(PertanyaanFAQ.objects.count(), len(FAQ_AWAL))

    def test_tiap_faq_ditemukan_lewat_pertanyaannya_sendiri(self):
        isi_faq_awal()
        for f in PertanyaanFAQ.objects.all():
            with self.subTest(f=f.pertanyaan):
                self.assertEqual(PertanyaanFAQ.cari(f.pertanyaan)[0], f)
                self.assertTrue(token(f.pertanyaan))

    def test_jawaban_pembayaran_tidak_lagi_bilang_hanya_di_kasir(self):
        isi_faq_awal()
        f = PertanyaanFAQ.objects.get(pertanyaan="Metode pembayaran apa saja yang tersedia?")
        self.assertIn("QRIS", f.jawaban)
        self.assertNotIn("Pembayaran diproses oleh kasir", f.jawaban)

    def test_tidak_menjanjikan_login_google(self):
        isi_faq_awal()
        f = PertanyaanFAQ.objects.get(pertanyaan="Bisakah daftar atau login dengan akun Google atau Facebook?")
        self.assertTrue(f.jawaban.startswith("Tidak"))


class PembaruanVersiLama(TestCase):
    """Baris dari isi awal versi lama di database yang sudah berjalan."""

    def _isi_versi_lama(self):
        for urutan, (kategori, pertanyaan, jawaban, kata_kunci) in enumerate(VERSI_LAMA, start=1):
            PertanyaanFAQ.objects.create(kategori=kategori, pertanyaan=pertanyaan, jawaban=jawaban,
                                         kata_kunci=kata_kunci, urutan=urutan)

    def test_jawaban_lama_yang_belum_diubah_diperbarui(self):
        self._isi_versi_lama()
        isi_faq_awal()
        f = PertanyaanFAQ.objects.get(pertanyaan="Metode pembayaran apa saja yang tersedia?")
        baru = next(j for _, p, j, _ in FAQ_AWAL if p == f.pertanyaan)
        self.assertEqual(f.jawaban, baru)

    def test_kategori_ikut_dipindah(self):
        self._isi_versi_lama()
        isi_faq_awal()
        f = PertanyaanFAQ.objects.get(pertanyaan="Bagaimana cara mendaftarkan kendaraan saya?")
        self.assertEqual(f.kategori, PertanyaanFAQ.KATEGORI_KENDARAAN)

    def test_jawaban_yang_sudah_diubah_admin_dibiarkan(self):
        self._isi_versi_lama()
        f = PertanyaanFAQ.objects.get(pertanyaan="Metode pembayaran apa saja yang tersedia?")
        f.jawaban = "Ketentuan bengkel kami: ..."
        f.save()
        isi_faq_awal()
        f.refresh_from_db()
        self.assertEqual(f.jawaban, "Ketentuan bengkel kami: ...")
        self.assertEqual(PertanyaanFAQ.objects.filter(pertanyaan=f.pertanyaan).count(), 1)

    def test_pertanyaan_yang_diganti_kalimatnya_tidak_jadi_dobel(self):
        self._isi_versi_lama()
        isi_faq_awal()
        self.assertFalse(PertanyaanFAQ.objects.filter(
            pertanyaan="Berapa biaya servis dan kapan saya membayar?").exists())
        self.assertEqual(PertanyaanFAQ.objects.filter(
            pertanyaan="Bagaimana biaya servis dihitung?").count(), 1)
        self.assertEqual(PertanyaanFAQ.objects.count(), len(FAQ_AWAL))

    def test_pertanyaan_diganti_tapi_jawabannya_diubah_admin_juga_tidak_dobel(self):
        self._isi_versi_lama()
        f = PertanyaanFAQ.objects.get(pertanyaan="Berapa biaya servis dan kapan saya membayar?")
        f.jawaban = "Versi admin"
        f.save()
        isi_faq_awal()
        f.refresh_from_db()
        self.assertEqual((f.pertanyaan, f.jawaban), ("Berapa biaya servis dan kapan saya membayar?", "Versi admin"))
        self.assertFalse(PertanyaanFAQ.objects.filter(pertanyaan="Bagaimana biaya servis dihitung?").exists())
        self.assertEqual(PertanyaanFAQ.objects.count(), len(FAQ_AWAL))

    def test_dijalankan_berulang_tetap_stabil(self):
        self._isi_versi_lama()
        isi_faq_awal()
        self.assertEqual(isi_faq_awal(), 0)
        self.assertEqual(PertanyaanFAQ.objects.count(), len(FAQ_AWAL))


class Placeholder(SimpleTestCase):
    INFO = {"alamat_bengkel": "Jl. Contoh 1", "telepon_bengkel": "+62 811",
            "jam_buka": [("Senin - Jumat", "08.00 - 20.00"), ("Sabtu", "10.00 - 16.00")]}

    def test_diisi_dari_info_bengkel(self):
        self.assertEqual(isi_placeholder("Alamat: {alamat_bengkel}. Telepon {telepon_bengkel}.", self.INFO),
                         "Alamat: Jl. Contoh 1. Telepon +62 811.")

    def test_jam_buka_dijadikan_kalimat(self):
        self.assertEqual(isi_placeholder("{jam_buka}", self.INFO),
                         "Senin - Jumat 08.00 - 20.00; Sabtu 10.00 - 16.00")

    def test_placeholder_tidak_dikenal_dibiarkan(self):
        self.assertEqual(isi_placeholder("Hubungi {tidak_ada} atau {}", self.INFO), "Hubungi {tidak_ada} atau {}")

    def test_kurung_kurawal_tanpa_nama_tidak_error(self):
        self.assertEqual(isi_placeholder("{ alamat } {{x}}", self.INFO), "{ alamat } {{x}}")


class PlaceholderDiChat(TestCase):
    def test_jawaban_info_bengkel_terisi_saat_dikirim(self):
        isi_faq_awal()
        info = info_bengkel(None)
        hasil = self.client.get("/faq/cari/", {"q": "alamat bengkel dmn"}).json()["hasil"]
        self.assertIn(info["alamat_bengkel"], hasil[0]["jawaban"])
        self.assertNotIn("{alamat_bengkel}", hasil[0]["jawaban"])
        daftar = self.client.get("/faq/daftar/").content.decode()
        self.assertNotIn("{telepon_bengkel}", daftar)

    def test_database_tetap_menyimpan_placeholder(self):
        isi_faq_awal()
        self.assertIn("{alamat_bengkel}", PertanyaanFAQ.objects.get(pertanyaan="Di mana alamat bengkel?").jawaban)
