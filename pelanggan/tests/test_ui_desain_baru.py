"""Persetujuan Diagnosis, Riwayat Service, dan Detail Riwayat mengikuti desain
baru (ui-pelanggan-update).

- Persetujuan: kartu per transaksi berisi pemeriksa, keluhan, catatan
  diagnosis, tabel estimasi biaya (sparepart + jasa), dan centang persetujuan
  yang wajib dicentang sebelum "Setuju & Lanjutkan".
- Riwayat: kolom pencarian (kode, merk, model, nomor polisi), ringkasan
  "Menampilkan x hingga y dari z data", dan tautan Lihat Nota / Detail.
- Detail: kontak digabung ke kartu Kendaraan & Mekanik di bagian atas.
"""
from django.urls import reverse

from kendaraan.models import Mobil
from mekanik.models import JenisServis
from sparepart.models import Sparepart

from .test_detail_riwayat import NOMOR_BENGKEL, Dasar, T


class PersetujuanDiagnosis(Dasar):
    def setUp(self):
        super().setUp()
        self.t = self.di_bengkel()
        self.t.input_diagnosis("Kampas rem habis", "Segera ganti kampas")
        self.url = reverse("persetujuan_diagnosis")

    def test_kepala_kartu_dan_pemeriksa(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Perlu Persetujuan Anda")
        self.assertContains(r, "Tanggal Pemeriksaan")
        self.assertContains(r, "Pemeriksa")
        self.assertContains(r, "Andi")
        self.assertContains(r, "Keluhan Awal Pelanggan")
        self.assertContains(r, "Catatan Diagnosis Mekanik")
        self.assertContains(r, "Kampas rem habis")
        self.assertContains(r, "Segera ganti kampas")

    def test_tabel_estimasi_berisi_sparepart_dan_jasa(self):
        # Baris dibuat langsung (bukan lewat tambah_layanan) karena yang diuji
        # hanya tampilannya, bukan aturan status.
        jasa = JenisServis.objects.create(nama_servis="Jasa Ganti Kampas", harga=35000,
                                          estimasi_waktu=30)
        self.t.detail_servis.create(jenis_servis=jasa, jumlah=1)
        part = Sparepart.objects.create(kode="KR-01", nama="Kampas Rem Depan", kategori="Rem",
                                        harga=55000, stok=5, stok_minimum=1)
        self.t.detail_sparepart.create(sparepart=part, jumlah=1)
        r = self.client.get(self.url)
        self.assertContains(r, "Estimasi Biaya Perbaikan")
        self.assertContains(r, "Kampas Rem Depan")
        self.assertContains(r, "Jasa Ganti Kampas")
        self.assertContains(r, "Total Estimasi Biaya")

    def test_centang_wajib_sebelum_setuju(self):
        isi = self.client.get(self.url).content.decode()
        self.assertIn(f'form="setuju-{self.t.pk}" required', isi)
        self.assertIn("Setuju &amp; Lanjutkan", isi)
        self.assertIn(">Tolak<", isi)


class RiwayatServis(Dasar):
    def setUp(self):
        super().setUp()
        self.a = self.di_bengkel()
        mobil = Mobil.objects.create(
            pelanggan=self.p, no_polisi="KT 5678 DEF", merk="Honda", model_kendaraan="Brio",
            tahun=2021, jumlah_pintu=5, jenis_mobil="Hatchback")
        self.b = T.buka(keterangan="x", oleh=self.kasir, pelanggan=self.p, kendaraan=mobil,
                        keluhan="AC panas", tipe_layanan=T.TIPE_DI_BENGKEL)
        self.url = reverse("riwayat_service")

    def test_ringkasan_jumlah_data(self):
        self.assertContains(self.client.get(self.url), "Menampilkan 1 hingga 2 dari 2 data")

    def test_cari_nomor_polisi(self):
        r = self.client.get(self.url, {"q": "5678"})
        self.assertContains(r, self.b.kode_transaksi)
        self.assertNotContains(r, self.a.kode_transaksi)

    def test_cari_kode_transaksi(self):
        r = self.client.get(self.url, {"q": self.a.kode_transaksi})
        self.assertContains(r, self.a.kode_transaksi)
        self.assertNotContains(r, self.b.kode_transaksi)

    def test_kolom_pencarian_ada(self):
        self.assertContains(self.client.get(self.url), 'name="q"')

    def test_hasil_kosong(self):
        self.assertContains(self.client.get(self.url, {"q": "tidak-ada"}), "Tidak ada servis yang cocok")


class DetailKontakDiAtas(Dasar):
    def test_kontak_di_kartu_kendaraan_mekanik(self):
        isi = self.buka(self.di_bengkel()).content.decode()
        self.assertNotIn("<h3>Kontak</h3>", isi)
        kartu = isi.index("<h3>Kendaraan &amp; Mekanik</h3>")
        nomor = isi.index(NOMOR_BENGKEL)
        self.assertGreater(nomor, kartu)
        self.assertLess(nomor, isi.index("<h3>Diagnosis &amp; Rekomendasi</h3>"))
