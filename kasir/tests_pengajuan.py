"""Uji halaman FR-31: pelanggan mengajukan, kasir menerima atau menolak.

Yang diuji di sini adalah sisi halaman: siapa boleh membuka apa, apakah form
menolak data yang tidak sah, dan apakah tombol Terima/Tolak hanya bisa lewat
POST. Aturan objeknya sendiri diuji di servis/tests_pengajuan.py.
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Pelanggan, User
from kendaraan.models import Motor
from servis.models import PengajuanServis, TransaksiServis

SANDI = "rahasia12345"


class AlurPengajuanTest(TestCase):
    def setUp(self):
        self.user_pel = User.objects.create_user(
            username="pel1", password=SANDI, role=User.ROLE_PELANGGAN
        )
        self.pelanggan = Pelanggan.objects.create(user=self.user_pel)

        self.user_lain = User.objects.create_user(
            username="pel2", password=SANDI, role=User.ROLE_PELANGGAN
        )
        self.pelanggan_lain = Pelanggan.objects.create(user=self.user_lain)

        self.user_kasir = User.objects.create_user(
            username="kas1", password=SANDI, role=User.ROLE_KASIR
        )
        self.user_mekanik = User.objects.create_user(
            username="mek1", password=SANDI, role=User.ROLE_MEKANIK
        )

        self.kendaraan = self._motor(self.pelanggan, "KT 10 AA")
        self.kendaraan_lain = self._motor(self.pelanggan_lain, "KT 20 BB")

    def _motor(self, pemilik, polisi):
        return Motor.objects.create(
            pelanggan=pemilik, no_polisi=polisi, merk="Honda",
            model_kendaraan="Vario", tahun=2022, jenis_motor="Matic",
            kapasitas_mesin=125,
        )

    def _ajukan(self, kendaraan=None, keluhan="Rem belakang bunyi berdecit"):
        return self.client.post(reverse("ajukan_servis"), {
            "kendaraan": f"motor:{(kendaraan or self.kendaraan).pk}",
            "keluhan": keluhan,
            "tanggal_rencana_datang": "",
        })

    # ---------- hak akses ----------

    def test_halaman_pelanggan_hanya_untuk_pelanggan(self):
        self.client.login(username="kas1", password=SANDI)
        self.assertEqual(self.client.get(reverse("ajukan_servis")).status_code, 302)

    def test_halaman_kasir_hanya_untuk_kasir(self):
        for username in ("pel1", "mek1"):
            self.client.login(username=username, password=SANDI)
            self.assertEqual(
                self.client.get(reverse("kasir_pengajuan_daftar")).status_code, 302,
                f"{username} seharusnya tidak boleh membuka daftar pengajuan kasir",
            )

    def test_tamu_diarahkan_ke_login(self):
        self.assertEqual(self.client.get(reverse("ajukan_servis")).status_code, 302)

    # ---------- pelanggan mengajukan ----------

    def test_pelanggan_bisa_mengajukan(self):
        self.client.login(username="pel1", password=SANDI)
        respons = self._ajukan()
        self.assertRedirects(respons, reverse("pengajuan_saya"))

        pengajuan = PengajuanServis.objects.get(kendaraan=self.kendaraan)
        self.assertEqual(pengajuan.pelanggan, self.pelanggan)
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_MENUNGGU)

    def test_tidak_bisa_mengajukan_kendaraan_orang_lain(self):
        self.client.login(username="pel1", password=SANDI)
        self._ajukan(kendaraan=self.kendaraan_lain)
        self.assertFalse(
            PengajuanServis.objects.filter(kendaraan=self.kendaraan_lain).exists()
        )

    def test_tidak_bisa_mengajukan_dua_kali_untuk_kendaraan_sama(self):
        self.client.login(username="pel1", password=SANDI)
        self._ajukan()
        self._ajukan(keluhan="Keluhan lain lagi")
        self.assertEqual(
            PengajuanServis.objects.filter(kendaraan=self.kendaraan).count(), 1
        )

    def test_keluhan_terlalu_pendek_ditolak(self):
        self.client.login(username="pel1", password=SANDI)
        self._ajukan(keluhan="abc")
        self.assertFalse(PengajuanServis.objects.exists())

    def test_tanggal_rencana_di_masa_lalu_ditolak(self):
        self.client.login(username="pel1", password=SANDI)
        self.client.post(reverse("ajukan_servis"), {
            "kendaraan": f"motor:{self.kendaraan.pk}",
            "keluhan": "Oli mesin bocor halus",
            "tanggal_rencana_datang": "2020-01-01",
        })
        self.assertFalse(PengajuanServis.objects.exists())

    # ---------- kasir memproses ----------

    def _pengajuan_menunggu(self):
        return PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.kendaraan,
            keluhan="Rem belakang bunyi berdecit",
        )

    def test_kasir_terima_membuat_transaksi(self):
        pengajuan = self._pengajuan_menunggu()
        self.client.login(username="kas1", password=SANDI)
        respons = self.client.post(
            reverse("kasir_pengajuan_terima", args=[pengajuan.pk])
        )

        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DITERIMA)
        self.assertIsNotNone(pengajuan.transaksi)
        self.assertRedirects(
            respons,
            reverse("kasir_transaksi_detail", args=[pengajuan.transaksi.pk]),
        )

    def test_terima_wajib_post(self):
        pengajuan = self._pengajuan_menunggu()
        self.client.login(username="kas1", password=SANDI)
        respons = self.client.get(
            reverse("kasir_pengajuan_terima", args=[pengajuan.pk])
        )
        self.assertEqual(respons.status_code, 405)
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_MENUNGGU)

    def test_kasir_tolak_wajib_mengisi_alasan(self):
        pengajuan = self._pengajuan_menunggu()
        self.client.login(username="kas1", password=SANDI)
        self.client.post(
            reverse("kasir_pengajuan_tolak", args=[pengajuan.pk]), {"alasan": ""}
        )
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_MENUNGGU)
        self.assertEqual(TransaksiServis.objects.count(), 0)

    def test_kasir_tolak_dengan_alasan(self):
        pengajuan = self._pengajuan_menunggu()
        self.client.login(username="kas1", password=SANDI)
        self.client.post(
            reverse("kasir_pengajuan_tolak", args=[pengajuan.pk]),
            {"alasan": "Bengkel penuh sampai hari Senin."},
        )
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DITOLAK)
        self.assertEqual(TransaksiServis.objects.count(), 0)

    def test_alasan_penolakan_terbaca_pelanggan(self):
        pengajuan = self._pengajuan_menunggu()
        pengajuan.tolak(self.user_kasir, "Bengkel penuh sampai hari Senin.")

        self.client.login(username="pel1", password=SANDI)
        isi = self.client.get(reverse("pengajuan_saya")).content.decode()
        self.assertIn("Bengkel penuh sampai hari Senin.", isi)

    # ---------- pembatalan oleh pelanggan ----------

    def test_pelanggan_bisa_membatalkan_pengajuannya(self):
        pengajuan = self._pengajuan_menunggu()
        self.client.login(username="pel1", password=SANDI)
        self.client.post(reverse("batalkan_pengajuan", args=[pengajuan.pk]))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_DIBATALKAN)

    def test_pelanggan_lain_tidak_bisa_membatalkan(self):
        pengajuan = self._pengajuan_menunggu()
        self.client.login(username="pel2", password=SANDI)
        respons = self.client.post(reverse("batalkan_pengajuan", args=[pengajuan.pk]))
        self.assertEqual(respons.status_code, 404)
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.status, PengajuanServis.STATUS_MENUNGGU)

    # ---------- filter status pada daftar kasir ----------

    def test_daftar_kasir_default_hanya_yang_menunggu(self):
        menunggu = self._pengajuan_menunggu()
        ditolak = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.kendaraan_lain,
            keluhan="Sudah ditolak sebelumnya",
        )
        ditolak.tolak(self.user_kasir, "Bengkel penuh.")

        self.client.login(username="kas1", password=SANDI)
        daftar = self.client.get(reverse("kasir_pengajuan_daftar")).context["daftar"]
        self.assertEqual(list(daftar), [menunggu])

    def test_pilihan_semua_menampilkan_seluruh_status(self):
        """'— Semua —' mengirim status kosong; itu harus berarti semua, bukan
        kembali ke default 'menunggu'."""
        self._pengajuan_menunggu()
        ditolak = PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.kendaraan_lain,
            keluhan="Sudah ditolak sebelumnya",
        )
        ditolak.tolak(self.user_kasir, "Bengkel penuh.")

        self.client.login(username="kas1", password=SANDI)
        daftar = self.client.get(
            reverse("kasir_pengajuan_daftar") + "?status="
        ).context["daftar"]
        self.assertEqual(len(list(daftar)), 2)

    def test_status_ngawur_diabaikan(self):
        self._pengajuan_menunggu()
        self.client.login(username="kas1", password=SANDI)
        respons = self.client.get(
            reverse("kasir_pengajuan_daftar") + "?status=NGAWUR"
        )
        self.assertEqual(respons.status_code, 200)
        self.assertEqual(respons.context["status_terpilih"], "")

    # ---------- badge navbar ----------

    def test_badge_jumlah_pengajuan_muncul_untuk_kasir(self):
        self._pengajuan_menunggu()
        self.client.login(username="kas1", password=SANDI)
        isi = self.client.get(reverse("kasir_dashboard")).content.decode()
        self.assertIn("pengajuan servis", isi.lower())

    def test_context_processor_tidak_jalan_untuk_role_lain(self):
        self._pengajuan_menunggu()
        self.client.login(username="pel1", password=SANDI)
        respons = self.client.get(reverse("pengajuan_saya"))
        self.assertNotIn("jumlah_pengajuan_menunggu", respons.context)
