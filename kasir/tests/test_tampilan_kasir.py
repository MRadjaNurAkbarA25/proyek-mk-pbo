"""Tampilan baru halaman kasir (bagian a): beranda, daftar, dan detail transaksi.

Angka beranda, badge pembayaran, dan susunan halaman. Nama tampil sudah diuji
di test_nama_tampil.py.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Mekanik, Pelanggan
from kendaraan.models import Motor
from pembayaran.models import BuktiPembayaran, Pembayaran
from servis.models import PengajuanServis, TransaksiServis

GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00"
       b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


class DasarKasir(TestCase):
    def setUp(self):
        User = get_user_model()
        self.kasir = User.objects.create_user(username="kasir", password="x", role=User.ROLE_KASIR)
        self.pelanggan = Pelanggan.objects.create(user=User.objects.create_user(
            username="pel", password="x", role=User.ROLE_PELANGGAN, first_name="Siti"))
        self.mekanik = Mekanik.objects.create(user=User.objects.create_user(
            username="mek", password="x", role=User.ROLE_MEKANIK, first_name="Budi"))
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1 AA", merk="Honda", model_kendaraan="Beat",
            tahun=2021, jenis_motor="Matic", kapasitas_mesin=110)
        self.client.force_login(self.kasir)

    def buat(self, kode, status, **lain):
        lain.setdefault("pelanggan", self.pelanggan)
        lain.setdefault("kendaraan", self.motor)
        return TransaksiServis.objects.create(kode_transaksi=kode, status=status,
                                              total_biaya=Decimal("100000"), **lain)

    def bukti(self, transaksi):
        return BuktiPembayaran.objects.create(
            transaksi=transaksi, jenis=BuktiPembayaran.JENIS_BANK, nama_penyedia="BRI",
            nomor_referensi="REF-" + transaksi.kode_transaksi,
            berkas=SimpleUploadedFile("bukti.gif", GIF, content_type="image/gif"))


class BerandaKasir(DasarKasir):
    def setUp(self):
        super().setUp()
        S = TransaksiServis
        self.buat("TRX-ANTRI", S.STATUS_MENUNGGU)                                  # antrian
        self.buat("TRX-BELUMTIBA", S.STATUS_MENUNGGU, kendaraan_hadir=False)       # belum antri
        self.buat("TRX-DIPEGANG", S.STATUS_MENUNGGU, mekanik=self.mekanik)         # sudah diambil
        self.belum_lunas = self.buat("TRX-HUTANG", S.STATUS_SELESAI)
        lunas = self.buat("TRX-LUNAS", S.STATUS_SELESAI)
        Pembayaran.buat(lunas, Pembayaran.METODE_CASH, uang_dibayar=Decimal("100000"))
        self.bukti(self.buat("TRX-BUKTI", S.STATUS_SELESAI))
        PengajuanServis.objects.create(pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="rem")

    def test_angka_empat_kartu(self):
        k = self.client.get(reverse("kasir_dashboard")).context
        self.assertEqual(k["jumlah_antrian"], 1)
        self.assertEqual(k["jumlah_pengajuan_menunggu"], 1)
        self.assertEqual(k["jumlah_bukti_menunggu"], 1)
        # TRX-HUTANG dan TRX-BUKTI: selesai, belum ada Pembayaran.
        self.assertEqual(k["jumlah_belum_lunas"], 2)

    def test_kartu_bisa_diklik(self):
        isi = self.client.get(reverse("kasir_dashboard")).content.decode()
        for url in (reverse("kasir_transaksi_daftar"), reverse("kasir_pengajuan_daftar"),
                    reverse("pembayaran_verifikasi_daftar")):
            with self.subTest(url=url):
                self.assertIn(f'href="{url}', isi)

    def test_lima_transaksi_terakhir_di_tabel_bersama(self):
        respons = self.client.get(reverse("kasir_dashboard"))
        self.assertEqual(len(respons.context["transaksi_terbaru"]), 5)
        self.assertContains(respons, 'class="tabel-data"')

    def test_judul_bergaya_dasbor_admin(self):
        self.assertContains(self.client.get(reverse("kasir_dashboard")), '<h1 class="h3 mb-1">')


class DaftarTransaksi(DasarKasir):
    def _baris(self, kode):
        isi = self.client.get(reverse("kasir_transaksi_daftar")).content.decode()
        return isi.split(kode, 1)[1].split("</tr>", 1)[0]

    def test_tabel_bersama_dan_kode_tidak_terpotong(self):
        t = self.buat("TRX-20261027-00001", TransaksiServis.STATUS_MENUNGGU)
        respons = self.client.get(reverse("kasir_transaksi_daftar"))
        self.assertContains(respons, 'class="tabel-data"')
        self.assertContains(respons, f'class="tabel-id nowrap" href="{reverse("kasir_transaksi_detail", args=[t.pk])}"')

    def test_badge_pembayaran(self):
        S = TransaksiServis
        lunas = self.buat("TRX-A-LUNAS", S.STATUS_SELESAI)
        Pembayaran.buat(lunas, Pembayaran.METODE_CASH, uang_dibayar=Decimal("100000"))
        self.buat("TRX-B-HUTANG", S.STATUS_SELESAI)
        self.bukti(self.buat("TRX-C-BUKTI", S.STATUS_SELESAI))
        self.buat("TRX-D-JALAN", S.STATUS_DIKERJAKAN)
        self.assertIn('badge-st hijau">Lunas', self._baris("TRX-A-LUNAS"))
        self.assertIn('badge-st merah">Belum lunas', self._baris("TRX-B-HUTANG"))
        self.assertIn('badge-st kuning">Menunggu verifikasi', self._baris("TRX-C-BUKTI"))
        # Belum selesai: belum ada tagihan, jadi tidak diberi badge merah.
        self.assertNotIn("Belum lunas", self._baris("TRX-D-JALAN"))

    def test_kolom_tipe_layanan_dan_badge_status(self):
        self.buat("TRX-HS", TransaksiServis.STATUS_DIKERJAKAN, tipe_layanan=TransaksiServis.TIPE_HOME_SERVICE)
        baris = self._baris("TRX-HS")
        self.assertIn('pil biru">Home Service', baris)
        self.assertIn('badge-st biru">Dikerjakan', baris)

    def test_kosong_memakai_tampilan_kosong(self):
        self.assertContains(self.client.get(reverse("kasir_transaksi_daftar")), 'class="kosong"')


class DetailTransaksi(DasarKasir):
    def _isi(self, t):
        return self.client.get(reverse("kasir_transaksi_detail", args=[t.pk])).content.decode()

    def test_dua_kolom_dan_tombol_kembali_di_atas(self):
        isi = self._isi(self.buat("TRX-D1", TransaksiServis.STATUS_MENUNGGU))
        self.assertIn('class="dtl-grid"', isi)
        self.assertLess(isi.index('class="tautan-kembali"'), isi.index('class="dtl-grid"'))
        samping = isi.split('class="dtl-samping"', 1)[1]
        self.assertLess(samping.index("Total Biaya"), samping.index("Perkembangan Servis"))

    def test_proses_pembayaran_untuk_servis_bengkel_belum_lunas(self):
        t = self.buat("TRX-D2", TransaksiServis.STATUS_SELESAI)
        isi = self._isi(t)
        self.assertIn(reverse("pembayaran_bayar", args=[t.pk]), isi)
        self.assertIn("Belum lunas", isi)

    def test_lihat_nota_bila_lunas(self):
        t = self.buat("TRX-D3", TransaksiServis.STATUS_SELESAI)
        p = Pembayaran.buat(t, Pembayaran.METODE_CASH, uang_dibayar=Decimal("100000"))
        isi = self._isi(t)
        self.assertIn(reverse("pembayaran_nota", args=[p.pk]), isi)
        self.assertNotIn(reverse("pembayaran_bayar", args=[t.pk]), isi)

    def test_periksa_bukti_bila_ada_bukti_menunggu(self):
        t = self.buat("TRX-D4", TransaksiServis.STATUS_SELESAI)
        b = self.bukti(t)
        isi = self._isi(t)
        self.assertIn(reverse("pembayaran_verifikasi_detail", args=[b.pk]), isi)
        self.assertIn("Menunggu verifikasi", isi)
        self.assertNotIn(reverse("pembayaran_bayar", args=[t.pk]), isi)


# ---------------------------------------------------------------- bagian (b)

class CariDanBuat(DasarKasir):
    def test_hasil_cari_jadi_tabel_dengan_aksi_buat_transaksi(self):
        isi = self.client.get(reverse("kasir_cari_kendaraan"), {"q": "KT 1"}).content.decode()
        self.assertIn('class="tabel-data"', isi)
        self.assertIn("Siti", isi)
        self.assertIn(f'{reverse("kasir_transaksi_buat")}?no_polisi=KT%201%20AA', isi)

    def test_cari_tidak_ketemu_memakai_tampilan_kosong(self):
        self.assertContains(self.client.get(reverse("kasir_cari_kendaraan"), {"q": "ZZZ"}), 'class="kosong"')

    def test_buat_transaksi_terisi_dari_hasil_cari(self):
        respons = self.client.get(reverse("kasir_transaksi_buat"), {"no_polisi": "KT 1 AA"})
        self.assertContains(respons, 'value="KT 1 AA"')
        self.assertContains(respons, 'class="kartu')

    def test_form_cari_dan_buat_bergaya_kartu(self):
        for url in (reverse("kasir_cari_kendaraan"), reverse("kasir_transaksi_buat")):
            with self.subTest(url=url):
                respons = self.client.get(url)
                self.assertContains(respons, 'class="kartu')
                self.assertContains(respons, '<h1 class="h3 mb-1">')


class Pengajuan(DasarKasir):
    def test_tabel_bersama_tanpa_tabel_bootstrap_lama(self):
        PengajuanServis.objects.create(pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="rem")
        respons = self.client.get(reverse("kasir_pengajuan_daftar"))
        self.assertContains(respons, 'class="tabel-data"')
        self.assertNotContains(respons, "table-dark")

    def test_kosong_memakai_tampilan_kosong(self):
        self.assertContains(self.client.get(reverse("kasir_pengajuan_daftar")), 'class="kosong"')


class HalamanPembayaranKasir(DasarKasir):
    def test_bayar_form_dalam_kartu(self):
        t = self.buat("TRX-B1", TransaksiServis.STATUS_SELESAI)
        respons = self.client.get(reverse("pembayaran_bayar", args=[t.pk]))
        self.assertContains(respons, 'class="kartu')
        self.assertContains(respons, "Simpan Pembayaran")
        self.assertContains(respons, 'class="tautan-kembali"')

    def test_verifikasi_daftar_tabel_bersama(self):
        b = self.bukti(self.buat("TRX-V1", TransaksiServis.STATUS_SELESAI))
        respons = self.client.get(reverse("pembayaran_verifikasi_daftar"))
        self.assertContains(respons, 'class="tabel-data"')
        self.assertNotContains(respons, "table-dark")
        self.assertContains(respons, "KT 1 AA")
        self.assertContains(respons, reverse("pembayaran_verifikasi_detail", args=[b.pk]))

    def test_verifikasi_detail_bukti_di_kiri_tombol_di_kanan(self):
        b = self.bukti(self.buat("TRX-V2", TransaksiServis.STATUS_SELESAI))
        isi = self.client.get(reverse("pembayaran_verifikasi_detail", args=[b.pk])).content.decode()
        self.assertIn('class="dtl-grid', isi)
        utama, samping = isi.split('class="dtl-samping"', 1)
        self.assertIn(reverse("pembayaran_bukti_berkas", args=[b.pk]), utama.split('class="dtl-utama"', 1)[1])
        self.assertIn(reverse("pembayaran_verifikasi_setujui", args=[b.pk]), samping)

    def test_nota_siap_cetak(self):
        t = self.buat("TRX-N1", TransaksiServis.STATUS_SELESAI)
        p = Pembayaran.buat(t, Pembayaran.METODE_CASH, uang_dibayar=Decimal("100000"))
        respons = self.client.get(reverse("pembayaran_nota", args=[p.pk]))
        self.assertContains(respons, 'class="nota')
        self.assertContains(respons, "css/kasir.css")
        self.assertContains(respons, "window.print()")


# ------------------------------------------------- penyamaan tampilan & isi kosong

class BuatTransaksiDuaKolom(DasarKasir):
    """Form di kiri, penjelasan dan angka antrian di kanan; gaya ikut Data Kendaraan admin."""

    def isi(self):
        return self.client.get(reverse("kasir_transaksi_buat")).content.decode()

    def test_form_di_kiri_panel_penjelasan_di_kanan(self):
        utama, samping = self.isi().split('class="dtl-samping"', 1)
        self.assertIn('name="no_polisi"', utama.split('class="dtl-utama"', 1)[1])
        self.assertIn("Kapan kasir membuat transaksi?", samping)
        self.assertIn("Setelah disimpan", utama)

    def test_angka_antrian_sama_dengan_antrian_mekanik(self):
        self.buat("TRX-ANTRI", TransaksiServis.STATUS_MENUNGGU)
        self.buat("TRX-BELUM", TransaksiServis.STATUS_MENUNGGU, kendaraan_hadir=False)
        respons = self.client.get(reverse("kasir_transaksi_buat"))
        self.assertEqual(respons.context["jumlah_antrian"], 1)

    def test_isian_dan_tombol_bergaya_data_kendaraan(self):
        isi = self.isi()
        self.assertIn('class="form-control', isi)
        self.assertIn('class="btn btn-dark"', isi)


class VerifikasiRincianTagihan(DasarKasir):
    """Di bawah kartu bukti: rincian tagihan dan bukti lain untuk transaksi yang sama."""

    def setUp(self):
        super().setUp()
        from mekanik.models import JenisServis
        from servis.models import DetailServis
        from sparepart.models import DetailSparepart, Sparepart
        self.t = self.buat("TRX-R1", TransaksiServis.STATUS_SELESAI)
        js = JenisServis.objects.create(nama_servis="Ganti Oli", estimasi_waktu=30, harga=Decimal("50000"))
        DetailServis.objects.create(transaksi=self.t, jenis_servis=js, jumlah=1, harga=Decimal("50000"))
        sp = Sparepart.objects.create(kode="OLI1", nama="Oli Mesin", kategori="Oli", harga=Decimal("50000"))
        DetailSparepart.objects.create(transaksi=self.t, sparepart=sp, jumlah=1,
                                       harga_satuan=Decimal("50000"), subtotal=Decimal("50000"))

    def utama(self, b):
        isi = self.client.get(reverse("pembayaran_verifikasi_detail", args=[b.pk])).content.decode()
        return isi.split('class="dtl-utama"', 1)[1].split('class="dtl-samping"', 1)[0]

    def test_rincian_layanan_dan_sparepart_di_bawah_bukti(self):
        utama = self.utama(self.bukti(self.t))
        self.assertIn("Rincian Tagihan", utama)
        self.assertIn("Ganti Oli", utama)
        self.assertIn("Oli Mesin", utama)

    def test_bukti_sebelumnya_untuk_transaksi_yang_sama(self):
        lama = self.bukti(self.t)
        BuktiPembayaran.objects.filter(pk=lama.pk).update(
            status=BuktiPembayaran.STATUS_DITOLAK, alasan_tolak="Nominal kurang")
        utama = self.utama(self.bukti(self.t))
        self.assertIn("Bukti sebelumnya", utama)
        self.assertIn("Nominal kurang", utama)
