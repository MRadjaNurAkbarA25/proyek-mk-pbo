"""FR-34: ketikan pengguna sungguhan terhadap isi FAQ awal.

Tiap baris: ketikan -> pertanyaan FAQ yang harus muncul di urutan pertama.
"""
from django.test import TestCase

from faq.data_awal import isi_faq_awal
from faq.models import PertanyaanFAQ
from faq.pencocokan import jenis_sapaan

KALIMAT = [
    # tabrakan servis vs service
    ("home service gimana caranya", "Bagaimana cara memesan Home Service?"),
    ("cara service motor di bengkel", "Bagaimana cara mengajukan servis di bengkel?"),
    ("berapa lama servis", "Berapa lama waktu pengerjaan servis?"),
    ("home service lama banget belum datang",
     "Mekanik Home Service belum menerima pesanan atau belum datang, bagaimana?"),
    ("servis panggilan ke rumah", "Apa itu Home Service?"),
    # ejaan tidak baku dan salah ketik
    ("gmn cara byr pake qris", "Bagaimana cara membayar lewat transfer atau QRIS?"),
    ("pembayran via transfer", "Bagaimana cara membayar lewat transfer atau QRIS?"),
    ("bukti tf saya ditolak", "Bukti pembayaran saya ditolak, apa yang harus dilakukan?"),
    ("lupa pw", "Saya lupa kata sandi, bagaimana cara mengatasinya?"),
    ("ga bisa login", "Saya tidak bisa login, apa yang harus dilakukan?"),
    ("cara regis akun", "Bagaimana cara mendaftar akun?"),
    ("plat nomor salah ganti gmn", "Bagaimana cara mengubah data kendaraan?"),
    ("hapus motor kok gak bisa", "Kenapa kendaraan saya tidak bisa dihapus?"),
    ("jam brp buka", "Jam berapa bengkel buka?"),
    ("alamat bengkel dmn", "Di mana alamat bengkel?"),
    # servis di bengkel
    ("berapa lama servis rem", "Berapa lama waktu pengerjaan servis?"),
    ("batas datang ke bengkel berapa hari", "Berapa lama kendaraan boleh datang setelah pengajuan diterima?"),
    ("kenapa servis saya dibatalkan otomatis", "Berapa lama kendaraan boleh datang setelah pengajuan diterima?"),
    ("cara cancel pengajuan", "Bagaimana cara membatalkan pengajuan servis?"),
    ("mau ganti tanggal datang", "Bisakah saya mengubah tanggal rencana datang?"),
    ("pengajuan saya ditolak kasir", "Kenapa pengajuan servis saya ditolak?"),
    ("motor saya gak bisa diajukan servis", "Kenapa kendaraan saya tidak bisa diajukan servis?"),
    ("cara setuju diagnosa", "Bagaimana cara menyetujui atau menolak diagnosis mekanik?"),
    ("arti status menunggu konfirmasi", "Apa arti status servis saya?"),
    ("pantau perkembangan servis", "Bagaimana cara memantau perkembangan servis?"),
    ("tanya mekanik soal servis saya", "Bagaimana cara bertanya ke mekanik yang menangani servis saya?"),
    # home service
    ("pilih mekanik home service", "Bagaimana memilih mekanik untuk Home Service?"),
    ("habis pesan home service terus gimana", "Apa yang terjadi setelah saya memesan Home Service?"),
    ("nomor hp mekanik home service", "Bagaimana cara menghubungi mekanik Home Service?"),
    ("home service dilanjut di bengkel", "Apa yang terjadi jika Home Service harus dilanjutkan di bengkel?"),
    # kendaraan
    ("tambah kendaraan baru", "Bagaimana cara mendaftarkan kendaraan saya?"),
    ("bedanya mobil dan motor", "Apa bedanya mendaftarkan mobil dan motor?"),
    # pembayaran
    ("bisa bayar pakai apa aja", "Metode pembayaran apa saja yang tersedia?"),
    ("kapan bayar servis", "Kapan saya harus membayar servis?"),
    ("format bukti transfer apa saja", "Bukti pembayaran seperti apa yang diterima?"),
    ("sudah kirim bukti bayar terus apa", "Apa yang terjadi setelah saya mengirim bukti pembayaran?"),
    ("kirim bukti lagi", "Bisakah saya mengirim bukti pembayaran lagi sebelum diperiksa?"),
    ("bayar tunai ke mekanik home service", "Bagaimana cara membayar Home Service?"),
    ("lihat nota", "Bagaimana cara melihat nota pembayaran?"),
    # biaya dan sparepart
    ("biaya servis dihitung dari apa", "Bagaimana biaya servis dihitung?"),
    ("kapan tahu total biaya", "Kapan saya tahu total biaya servis?"),
    ("biaya nambah setelah setuju diagnosis", "Apakah biaya bisa bertambah setelah diagnosis disetujui?"),
    ("daftar harga layanan", "Di mana saya bisa melihat daftar harga layanan?"),
    ("harga sudah termasuk sparepart belum", "Apakah harga layanan sudah termasuk sparepart?"),
    # akun
    ("login pakai google", "Bisakah daftar atau login dengan akun Google atau Facebook?"),
    ("ganti password", "Bagaimana cara mengganti kata sandi?"),
    ("ubah foto profil", "Bagaimana cara mengubah data profil dan foto?"),
    # info bengkel
    ("nomor wa bengkel", "Bagaimana cara menghubungi bengkel?"),
    ("home service melayani daerah mana", "Daerah mana saja yang dilayani Home Service?"),
]

NEGATIF = ["harga saham hari ini", "asdfgh", "", "   ", "saya mau dong", "apa yang bisa", "???"]


class KalimatNyata(TestCase):
    @classmethod
    def setUpTestData(cls):
        isi_faq_awal()

    def test_tabel_cukup_banyak(self):
        self.assertGreaterEqual(len(KALIMAT), 40)

    def test_faq_yang_diharapkan_di_urutan_pertama(self):
        semua = set(PertanyaanFAQ.objects.values_list("pertanyaan", flat=True))
        for ketikan, harapan in KALIMAT:
            with self.subTest(ketikan=ketikan):
                self.assertIn(harapan, semua)  # salah ketik di tabel ini, bukan di pencocokan
                hasil = PertanyaanFAQ.cari(ketikan)
                self.assertTrue(hasil, "tidak ada hasil")
                self.assertEqual(hasil[0].pertanyaan, harapan)

    def test_home_service_tidak_ditarik_ke_servis_bengkel(self):
        for ketikan in ("home service gimana caranya", "servis panggilan ke rumah", "home servis"):
            with self.subTest(ketikan=ketikan):
                judul = [f.pertanyaan for f in PertanyaanFAQ.cari(ketikan)]
                self.assertNotIn("Bagaimana cara mengajukan servis di bengkel?", judul)

    def test_ketikan_acak_tidak_menghasilkan_apa_pun(self):
        for ketikan in NEGATIF:
            with self.subTest(ketikan=ketikan):
                self.assertEqual(PertanyaanFAQ.cari(ketikan), [])

    def test_sapaan_dan_terima_kasih(self):
        for ketikan, jenis in (("halo", "sapaan"), ("pagi kak", "sapaan"), ("permisi", "sapaan"),
                               ("makasih", "terima_kasih"), ("terima kasih banyak", "terima_kasih"),
                               ("thanks min", "terima_kasih")):
            with self.subTest(ketikan=ketikan):
                self.assertEqual(jenis_sapaan(ketikan), jenis)

    def test_sapaan_yang_membawa_pertanyaan_tetap_dicari(self):
        self.assertIsNone(jenis_sapaan("halo, cara bayar qris gimana"))
        self.assertEqual(PertanyaanFAQ.cari("halo, cara bayar qris gimana")[0].pertanyaan,
                         "Bagaimana cara membayar lewat transfer atau QRIS?")
