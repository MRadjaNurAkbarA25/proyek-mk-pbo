"""Alur pembayaran: cash dicatat petugas, non-tunai lewat bukti yang diverifikasi.

- Servis di bengkel: kasir mencatat cash.
- Home service: mekanik yang menanganinya mencatat cash.
- Transfer bank / e-money (QRIS): pelanggan mengunggah bukti, kasir ATAU
  admin memeriksa. Keputusan pertama yang final; ditolak berarti pelanggan
  mengulang dari memilih metode, dan bukti lamanya tetap tersimpan.
"""
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Mekanik, Pelanggan
from servis.models import TransaksiServis

from pembayaran.models import BuktiPembayaran, Pembayaran

TMP_BUKTI = tempfile.mkdtemp(prefix="bukti_tes_")


def berkas_png(nama="bukti.png", ukuran=None):
    isi = b"\x89PNG\r\n\x1a\n" + b"0" * (ukuran or 10)
    return SimpleUploadedFile(nama, isi, content_type="image/png")


@override_settings(BUKTI_BAYAR_ROOT=Path(TMP_BUKTI))
class DasarAlurBayar(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_BUKTI, ignore_errors=True)

    def setUp(self):
        User = get_user_model()
        buat = User.objects.create_user
        self.pelanggan = Pelanggan.objects.create(user=buat(
            username="siti", password="demo12345", role=User.ROLE_PELANGGAN))
        self.pelanggan_lain = Pelanggan.objects.create(user=buat(
            username="joko", password="demo12345", role=User.ROLE_PELANGGAN))
        self.kasir = buat(username="kasir", password="demo12345", role=User.ROLE_KASIR,
                          first_name="Kasir Ani")
        self.admin = buat(username="admin", password="demo12345", role=User.ROLE_ADMIN)
        self.mekanik = Mekanik.objects.create(user=buat(
            username="budi", password="demo12345", role=User.ROLE_MEKANIK))
        self.mekanik_lain = Mekanik.objects.create(user=buat(
            username="andi", password="demo12345", role=User.ROLE_MEKANIK))

    def transaksi(self, tipe=TransaksiServis.TIPE_DI_BENGKEL, status=TransaksiServis.STATUS_SELESAI):
        return TransaksiServis.objects.create(
            status=status, tipe_layanan=tipe, pelanggan=self.pelanggan,
            mekanik=self.mekanik, total_biaya=Decimal("150000"))

    def ajukan(self, transaksi, jenis=BuktiPembayaran.JENIS_BANK, penyedia="BRI"):
        return BuktiPembayaran.ajukan(
            transaksi, self.pelanggan, jenis=jenis, nama_penyedia=penyedia,
            nomor_referensi="REF123", berkas=berkas_png())


class CashTests(DasarAlurBayar):
    def test_kasir_mencatat_cash_servis_di_bengkel(self):
        t = self.transaksi()
        p = Pembayaran.catat_cash(t, Decimal("200000"), oleh=self.kasir)
        self.assertEqual(p.metode, Pembayaran.METODE_CASH)
        self.assertEqual(p.dicatat_oleh, self.kasir)
        self.assertEqual(p.detail().hitung_kembalian(), Decimal("50000"))

    def test_mekanik_tidak_mencatat_cash_servis_di_bengkel(self):
        with self.assertRaises(ValidationError):
            Pembayaran.catat_cash(self.transaksi(), Decimal("150000"), oleh=self.mekanik.user)

    def test_mekanik_penanganan_mencatat_cash_home_service(self):
        t = self.transaksi(TransaksiServis.TIPE_HOME_SERVICE)
        p = Pembayaran.catat_cash(t, Decimal("150000"), oleh=self.mekanik.user)
        self.assertEqual(p.dicatat_oleh, self.mekanik.user)

    def test_home_service_tidak_dicatat_kasir_atau_mekanik_lain(self):
        t = self.transaksi(TransaksiServis.TIPE_HOME_SERVICE)
        for orang in (self.kasir, self.mekanik_lain.user):
            with self.assertRaises(ValidationError, msg=orang.username):
                Pembayaran.catat_cash(t, Decimal("150000"), oleh=orang)
        self.assertFalse(Pembayaran.objects.exists())

    def test_cash_ditolak_selama_ada_bukti_menunggu(self):
        t = self.transaksi()
        self.ajukan(t)
        with self.assertRaises(ValidationError):
            Pembayaran.catat_cash(t, Decimal("150000"), oleh=self.kasir)

    def test_view_kasir_cash(self):
        t = self.transaksi()
        self.client.force_login(self.kasir)
        r = self.client.post(reverse("pembayaran_bayar", args=[t.pk]), {"uang_dibayar": "150000"})
        self.assertRedirects(r, reverse("pembayaran_nota", args=[Pembayaran.objects.get().pk]))

    def test_view_mekanik_cash_home_service(self):
        t = self.transaksi(TransaksiServis.TIPE_HOME_SERVICE)
        self.client.force_login(self.mekanik.user)
        r = self.client.post(reverse("pembayaran_cash_mekanik", args=[t.pk]), {"uang_dibayar": "150000"})
        self.assertRedirects(r, reverse("mekanik_detail", args=[t.pk]), fetch_redirect_response=False)
        self.assertEqual(Pembayaran.objects.get().dicatat_oleh, self.mekanik.user)


class BuktiNonTunaiTests(DasarAlurBayar):
    def test_ajukan_menunggu_dan_belum_lunas(self):
        t = self.transaksi()
        bukti = self.ajukan(t)
        self.assertEqual(bukti.status, BuktiPembayaran.STATUS_MENUNGGU)
        self.assertFalse(Pembayaran.objects.exists())
        # resolve(): di Windows %TEMP% bisa berupa nama pendek (LENOVO~1),
        # sedangkan penyimpanan privat memakai path yang sudah di-resolve.
        self.assertTrue(Path(bukti.berkas.path).is_relative_to(Path(TMP_BUKTI).resolve()))

    def test_ajukan_ditolak_bila_belum_selesai_atau_bukan_pemilik(self):
        with self.assertRaises(ValidationError):
            self.ajukan(self.transaksi(status=TransaksiServis.STATUS_DIKERJAKAN))
        with self.assertRaises(ValidationError):
            BuktiPembayaran.ajukan(
                self.transaksi(), self.pelanggan_lain, jenis=BuktiPembayaran.JENIS_BANK,
                nama_penyedia="BRI", nomor_referensi="X", berkas=berkas_png())

    def test_tidak_bisa_dua_bukti_menunggu(self):
        t = self.transaksi()
        self.ajukan(t)
        with self.assertRaises(ValidationError):
            self.ajukan(t)

    def test_setujui_bank_menjadi_transfer_lunas(self):
        t = self.transaksi()
        bukti = self.ajukan(t)
        p = bukti.setujui(self.kasir)
        bukti.refresh_from_db()
        self.assertEqual(bukti.status, BuktiPembayaran.STATUS_DISETUJUI)
        self.assertEqual(bukti.diperiksa_oleh, self.kasir)
        self.assertEqual(p.metode, Pembayaran.METODE_TRANSFER)
        self.assertEqual(p.detail().nomor_referensi, "REF123")
        self.assertEqual(p.dicatat_oleh, self.kasir)

    def test_setujui_e_money_menjadi_e_wallet(self):
        bukti = self.ajukan(self.transaksi(), jenis=BuktiPembayaran.JENIS_E_MONEY, penyedia="DANA")
        p = bukti.setujui(self.admin)
        self.assertEqual(p.metode, Pembayaran.METODE_EWALLET)
        self.assertEqual(p.detail().provider, "DANA")

    def test_pemeriksa_kedua_kalah(self):
        bukti = self.ajukan(self.transaksi())
        salinan = BuktiPembayaran.objects.get(pk=bukti.pk)  # dibuka admin sebelum kasir memutuskan
        bukti.setujui(self.kasir)
        with self.assertRaisesMessage(ValidationError, "Kasir Ani"):
            salinan.tolak(self.admin, "buram")
        self.assertEqual(Pembayaran.objects.count(), 1)

    def test_tolak_wajib_alasan_lalu_bisa_ajukan_ulang(self):
        t = self.transaksi()
        bukti = self.ajukan(t)
        with self.assertRaises(ValidationError):
            bukti.tolak(self.admin, "  ")
        bukti.tolak(self.admin, "Nominal tidak sesuai")
        bukti.refresh_from_db()
        self.assertEqual(bukti.status, BuktiPembayaran.STATUS_DITOLAK)
        self.assertEqual(bukti.alasan_tolak, "Nominal tidak sesuai")
        self.ajukan(t)
        self.assertEqual(t.bukti_pembayaran.count(), 2)
        self.assertFalse(Pembayaran.objects.exists())

    def test_referensi_yang_sudah_disetujui_tidak_bisa_dipakai_lagi(self):
        self.ajukan(self.transaksi()).setujui(self.kasir)
        with self.assertRaisesMessage(ValidationError, "sudah dipakai"):
            BuktiPembayaran.ajukan(
                self.transaksi(), self.pelanggan, jenis=BuktiPembayaran.JENIS_BANK,
                nama_penyedia="bri", nomor_referensi=" ref123 ", berkas=berkas_png())

    def test_dua_bukti_menunggu_dengan_referensi_sama_hanya_satu_disetujui(self):
        pertama = self.ajukan(self.transaksi())
        kedua = self.ajukan(self.transaksi())
        pertama.setujui(self.kasir)
        with self.assertRaisesMessage(ValidationError, "sudah dipakai"):
            kedua.setujui(self.kasir)
        kedua.refresh_from_db()
        self.assertEqual(kedua.status, BuktiPembayaran.STATUS_MENUNGGU)
        self.assertEqual(Pembayaran.objects.count(), 1)

    def test_referensi_sama_beda_penyedia_tetap_boleh(self):
        self.ajukan(self.transaksi()).setujui(self.kasir)
        self.ajukan(self.transaksi(), penyedia="BCA").setujui(self.kasir)
        self.assertEqual(Pembayaran.objects.count(), 2)

    def test_tidak_bisa_ajukan_setelah_lunas(self):
        t = self.transaksi()
        Pembayaran.catat_cash(t, Decimal("150000"), oleh=self.kasir)
        with self.assertRaises(ValidationError):
            self.ajukan(t)


class HalamanNonTunaiTests(DasarAlurBayar):
    def kirim(self, t, berkas, user=None):
        self.client.force_login(user or self.pelanggan.user)
        return self.client.post(reverse("pembayaran_nontunai", args=[t.pk]), {
            "jenis": BuktiPembayaran.JENIS_E_MONEY, "nama_penyedia": "OVO",
            "nomor_referensi": "OVO-1", "berkas": berkas,
        })

    def test_pelanggan_mengunggah_bukti(self):
        t = self.transaksi()
        self.client.force_login(self.pelanggan.user)
        self.assertContains(self.client.get(reverse("pembayaran_nontunai", args=[t.pk])), "QRIS")
        r = self.kirim(t, berkas_png())
        self.assertRedirects(r, reverse("riwayat_service_detail", args=[t.pk]), fetch_redirect_response=False)
        self.assertEqual(BuktiPembayaran.objects.get().nama_penyedia, "OVO")

    def test_berkas_salah_jenis_atau_terlalu_besar(self):
        t = self.transaksi()
        self.kirim(t, SimpleUploadedFile("virus.exe", b"MZ"))
        self.kirim(t, berkas_png(ukuran=2 * 1024 * 1024 + 1))
        self.assertFalse(BuktiPembayaran.objects.exists())

    def test_transaksi_orang_lain_404(self):
        r = self.kirim(self.transaksi(), berkas_png(), user=self.pelanggan_lain.user)
        self.assertEqual(r.status_code, 404)

    def test_akses_berkas_bukti(self):
        bukti = self.ajukan(self.transaksi())
        url = reverse("pembayaran_bukti_berkas", args=[bukti.pk])
        for orang in (self.pelanggan.user, self.kasir, self.admin):
            self.client.force_login(orang)
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, orang.username)
            r.close()
        for orang in (self.pelanggan_lain.user, self.mekanik.user):
            self.client.force_login(orang)
            self.assertIn(self.client.get(url).status_code, (302, 404), orang.username)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)


class HalamanVerifikasiTests(DasarAlurBayar):
    def test_hanya_kasir_dan_admin(self):
        url = reverse("pembayaran_verifikasi_daftar")
        for orang in (self.kasir, self.admin):
            self.client.force_login(orang)
            self.assertEqual(self.client.get(url).status_code, 200, orang.username)
        for orang in (self.mekanik.user, self.pelanggan.user):
            self.client.force_login(orang)
            self.assertEqual(self.client.get(url).status_code, 302, orang.username)

    def test_setujui_lewat_halaman(self):
        bukti = self.ajukan(self.transaksi())
        self.client.force_login(self.kasir)
        self.assertContains(self.client.get(reverse("pembayaran_verifikasi_daftar")), bukti.transaksi.kode_transaksi)
        r = self.client.post(reverse("pembayaran_verifikasi_setujui", args=[bukti.pk]))
        self.assertRedirects(r, reverse("pembayaran_nota", args=[Pembayaran.objects.get().pk]))

    def test_tolak_lewat_halaman_tampil_ke_pelanggan(self):
        t = self.transaksi()
        bukti = self.ajukan(t)
        self.client.force_login(self.admin)
        self.client.post(reverse("pembayaran_verifikasi_tolak", args=[bukti.pk]), {"alasan": "Bukti buram"})
        self.client.force_login(self.pelanggan.user)
        self.assertContains(self.client.get(reverse("riwayat_service_detail", args=[t.pk])), "Bukti buram")

    def test_halaman_periksa_bukti(self):
        bukti = self.ajukan(self.transaksi())
        self.client.force_login(self.admin)
        r = self.client.get(reverse("pembayaran_verifikasi_detail", args=[bukti.pk]))
        self.assertContains(r, "REF123")
        self.assertContains(r, reverse("pembayaran_verifikasi_setujui", args=[bukti.pk]))

    def test_kartu_cash_di_detail_mekanik(self):
        t = self.transaksi(TransaksiServis.TIPE_HOME_SERVICE)
        self.client.force_login(self.mekanik.user)
        url = reverse("mekanik_detail", args=[t.pk])
        self.assertContains(self.client.get(url), "Catat Cash")
        self.ajukan(t)
        self.assertNotContains(self.client.get(url), "Catat Cash")

    def test_badge_bukti_menunggu(self):
        self.ajukan(self.transaksi())
        self.client.force_login(self.kasir)
        r = self.client.get(reverse("pembayaran_verifikasi_daftar"))
        self.assertEqual(r.context["jumlah_bukti_menunggu"], 1)
