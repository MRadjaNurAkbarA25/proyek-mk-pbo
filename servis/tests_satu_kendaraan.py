"""Satu kendaraan hanya boleh punya satu pekerjaan berjalan.

Aturan ini dulu hanya dijaga di sisi Ajukan Servis. Home Service tidak
memeriksa apa pun, jadi kendaraan yang sedang diservis masih bisa
dipesankan home service, berkali-kali pula.

Tes di bawah menjaga KEEMPAT arah, bukan cuma arah yang bocor, supaya
lubang yang sama tidak terbuka lagi di sisi mana pun.
"""
from django.test import TestCase
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis


class DasarSatuKendaraan(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi", password="demo12345", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(
            username="kasir9", password="demo12345", role=User.ROLE_KASIR)
        mek_user = User.objects.create_user(
            username="mek9", password="demo12345", role=User.ROLE_MEKANIK)
        mek_user.first_name = "Rudi"
        mek_user.save()
        self.mekanik = Mekanik.objects.create(
            user=mek_user, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1234 ZZ",
            merk="Honda", model_kendaraan="Beat", tahun=2020,
            jenis_motor="Matic", kapasitas_mesin=110)

    def pesan_home_service(self):
        """Kirim form Home Service lewat HTTP, persis seperti pelanggan."""
        self.client.force_login(self.user)
        return self.client.post("/pelanggan/home-service/pesan/", {
            "kendaraan": f"motor:{self.motor.pk}",
            "mekanik": str(self.mekanik.pk),
            "keluhan": "Mesin tidak mau hidup sama sekali",
            "lokasi_servis": "Jl. Mawar No. 10, Samarinda",
        })

    def buat_transaksi_bengkel(self):
        return TransaksiServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor,
            keluhan="Rem blong",
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
            status=TransaksiServis.STATUS_MENUNGGU,
        )


class HomeServiceMenolakKendaraanYangSedangDipakai(DasarSatuKendaraan):
    def test_tidak_bisa_pesan_dua_kali_untuk_kendaraan_yang_sama(self):
        """Inti laporannya: dulu bisa sebanyak-banyaknya."""
        self.assertEqual(self.pesan_home_service().status_code, 302)
        self.assertEqual(TransaksiServis.objects.count(), 1)

        respons = self.pesan_home_service()
        self.assertEqual(respons.status_code, 200, "pesanan kedua seharusnya ditolak")
        self.assertContains(respons, "masih dalam proses servis")
        self.assertEqual(
            TransaksiServis.objects.count(), 1,
            "pesanan kedua tidak boleh membuat transaksi baru",
        )

    def test_tidak_bisa_pesan_kalau_sedang_servis_di_bengkel(self):
        self.buat_transaksi_bengkel()

        respons = self.pesan_home_service()
        self.assertEqual(respons.status_code, 200)
        self.assertContains(respons, "masih dalam proses servis")
        self.assertEqual(TransaksiServis.objects.count(), 1)

    def test_tidak_bisa_pesan_kalau_ada_pengajuan_menunggu_kasir(self):
        PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Oli bocor")

        respons = self.pesan_home_service()
        self.assertEqual(respons.status_code, 200)
        self.assertContains(respons, "menunggu persetujuan kasir")
        self.assertEqual(TransaksiServis.objects.count(), 0)

    def test_boleh_pesan_lagi_setelah_servis_sebelumnya_selesai(self):
        transaksi = self.buat_transaksi_bengkel()
        transaksi.status = TransaksiServis.STATUS_SELESAI
        transaksi.save(update_fields=["status"])

        self.assertEqual(self.pesan_home_service().status_code, 302)
        self.assertEqual(TransaksiServis.objects.count(), 2)


class AjukanServisTetapTerjaga(DasarSatuKendaraan):
    """Arah sebaliknya: jangan sampai rusak waktu aturannya disatukan."""

    def test_tidak_bisa_ajukan_kalau_ada_home_service_berjalan(self):
        self.assertEqual(self.pesan_home_service().status_code, 302)

        alasan = PengajuanServis.alasan_kendaraan_tidak_bisa(self.motor)
        self.assertIsNotNone(alasan)
        self.assertIn("masih dalam proses servis", alasan)

    def test_tidak_bisa_ajukan_dua_kali(self):
        PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Oli bocor")

        alasan = PengajuanServis.alasan_kendaraan_tidak_bisa(self.motor)
        self.assertIsNotNone(alasan)
        self.assertIn("menunggu persetujuan kasir", alasan)

    def test_kendaraan_bebas_boleh_diajukan(self):
        self.assertIsNone(PengajuanServis.alasan_kendaraan_tidak_bisa(self.motor))

    def test_kasir_tetap_bisa_menerima_pengajuan_itu_sendiri(self):
        """Pengajuan yang sedang diproses tidak boleh menghalangi dirinya sendiri."""
        pengajuan = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Oli bocor")

        self.assertIsNone(pengajuan.alasan_kendaraan_tidak_bisa_selain_ini())
        transaksi = pengajuan.terima(self.kasir)
        self.assertEqual(transaksi.kendaraan_id, self.motor.pk)

    def test_dua_pengajuan_menunggu_saling_mengunci_sampai_satu_ditolak(self):
        """Perilaku lama yang sengaja dipertahankan, bukan bug baru.

        Lewat form, pengajuan kedua untuk kendaraan yang sama memang tidak
        bisa dibuat. Dua pengajuan menunggu hanya mungkin dari data lama
        atau dari /admin/. Kalau itu terjadi, kasir tidak bisa menerima
        salah satunya sampai yang lain ditolak dulu — dan itu memang jalan
        keluarnya, bukan jalan buntu.
        """
        pertama = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Oli bocor")
        kedua = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Rem blong")

        self.assertIsNotNone(pertama.alasan_kendaraan_tidak_bisa_selain_ini())
        self.assertIsNotNone(kedua.alasan_kendaraan_tidak_bisa_selain_ini())

        kedua.tolak(self.kasir, "Dobel, sudah ada pengajuan lain.")

        self.assertIsNone(pertama.alasan_kendaraan_tidak_bisa_selain_ini())
        transaksi = pertama.terima(self.kasir)
        self.assertEqual(transaksi.kendaraan_id, self.motor.pk)
