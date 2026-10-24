"""FR-34: isi awal FAQ lewat seed_demo."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from faq.data_awal import FAQ_AWAL, isi_faq_awal
from faq.models import KATA_UMUM, PertanyaanFAQ


class IsiAwal(TestCase):
    def test_sekitar_lima_belas_faq_dan_semua_kategori_terisi(self):
        self.assertEqual(isi_faq_awal(), len(FAQ_AWAL))
        self.assertTrue(14 <= PertanyaanFAQ.objects.count() <= 16)
        kode_kategori = {kode for kode, _ in PertanyaanFAQ.KATEGORI_CHOICES}
        self.assertEqual(set(PertanyaanFAQ.objects.values_list("kategori", flat=True)), kode_kategori)

    def test_semua_lengkap_dan_aktif(self):
        isi_faq_awal()
        for f in PertanyaanFAQ.objects.all():
            self.assertTrue(f.aktif)
            self.assertTrue(f.jawaban.strip(), f.pertanyaan)
            self.assertTrue(f.kata_kunci.strip(), f.pertanyaan)

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

    def test_pertanyaan_awal_bisa_ditemukan_lewat_kata_kuncinya(self):
        """Tiap FAQ awal harus bisa ditemukan dengan mengetik pertanyaannya sendiri."""
        isi_faq_awal()
        for f in PertanyaanFAQ.objects.all():
            with self.subTest(f=f.pertanyaan):
                self.assertIn(f, PertanyaanFAQ.cari(f.pertanyaan))
                self.assertTrue(set(f.pertanyaan.lower().split()) - KATA_UMUM)
