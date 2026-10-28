"""seed_demo untuk presentasi: setiap fitur punya contohnya, dan --reset bisa diulang."""
import io
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from accounts.notifikasi import angka_badge
from kendaraan.models import Kendaraan, Mobil, Motor
from pembayaran.models import BuktiPembayaran, Pembayaran
from servis.models import PembaruanServis, PengajuanServis
from servis.models import TransaksiServis as T

TMP = tempfile.mkdtemp(prefix="bukti_seed_lengkap_")


def seed(**kw):
    call_command("seed_demo", verbosity=0, stdout=io.StringIO(), izinkan_di_server=True, **kw)


@override_settings(BUKTI_BAYAR_ROOT=Path(TMP))
class SeedLengkap(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def badge(self, username):
        request = RequestFactory().get("/")
        request.user = User.objects.get(username=username)
        return angka_badge(request)

    def test_1_pelanggan3_tanpa_kendaraan(self):
        rina = Pelanggan.objects.get(user__username="pelanggan3")
        self.assertFalse(Kendaraan.objects.filter(pelanggan=rina).exists())

    def test_2_pengajuan_menunggu_dan_ditolak_belum_dilihat(self):
        demo = PengajuanServis.objects.filter(keluhan__startswith="[DEMO] ", pelanggan__user__username="pelanggan2")
        self.assertEqual(
            (demo.filter(status=PengajuanServis.STATUS_MENUNGGU).count(),
             demo.filter(status=PengajuanServis.STATUS_DITOLAK, dilihat_pelanggan=False).count()), (1, 1))

    def test_3_home_service_baru_dan_menunggu_persetujuan_dengan_titik(self):
        hs = T.objects.filter(tipe_layanan=T.TIPE_HOME_SERVICE, lokasi_lat__isnull=False)
        self.assertEqual(
            (hs.filter(mekanik__user__username="mekanik2", status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK).count(),
             hs.filter(mekanik__user__username="mekanik1", status=T.STATUS_MENUNGGU_KONFIRMASI).count()), (1, 1))

    def test_4_profil_pelanggan1_beralamat_dan_bertitik(self):
        u = User.objects.get(username="pelanggan1")
        self.assertTrue(u.alamat and u.alamat_lat is not None and u.alamat_lng is not None)

    def test_5_kabar_mekanik_dan_pesan_pelanggan_di_transaksi_dikerjakan(self):
        t = T.objects.get(status=T.STATUS_DIKERJAKAN, keluhan__startswith="[DEMO] ")
        self.assertEqual(
            (t.pembaruan.filter(oleh=t.mekanik.user, tahap=PembaruanServis.TAHAP_PERBAIKAN).exclude(
                keterangan__startswith="Layanan").exists(),
             t.pembaruan.filter(pesan_pelanggan=True).exists()), (True, True))

    def test_6_lunas_transfer_disetujui(self):
        self.assertTrue(BuktiPembayaran.objects.filter(
            status=BuktiPembayaran.STATUS_DISETUJUI, jenis=BuktiPembayaran.JENIS_BANK,
            transaksi__pembayaran__metode=Pembayaran.METODE_TRANSFER).exists())

    def test_7_servis_bengkel_selesai_belum_dibayar_tanpa_bukti(self):
        self.assertTrue(T.belum_dibayar().filter(tipe_layanan=T.TIPE_DI_BENGKEL).exists())

    def test_8_riwayat_tiga_bulan_beragam_dan_tanggalnya_mundur(self):
        sekarang = timezone.now()
        riwayat = T.objects.filter(status=T.STATUS_SELESAI, pembayaran__isnull=False,
                                   tanggal__gte=sekarang - timedelta(days=100),
                                   tanggal__lte=sekarang - timedelta(days=7))
        jenis = {d.jenis_servis_id for t in riwayat for d in t.detail_servis.all()}
        tipe = {type(t.kendaraan.spesifik()) for t in riwayat}
        linimasa_mundur = not PembaruanServis.objects.filter(
            transaksi__in=riwayat, waktu__gt=sekarang - timedelta(days=7)).exists()
        bayar_mundur = not Pembayaran.objects.filter(
            transaksi__in=riwayat, tanggal__gt=sekarang - timedelta(days=7)).exists()
        self.assertEqual(
            (4 <= riwayat.count() <= 6, riwayat.values("mekanik").distinct().count() >= 2, len(jenis) >= 3,
             tipe == {Mobil, Motor}, riwayat.filter(berawal_home_service=True,
                                                    tipe_layanan=T.TIPE_DI_BENGKEL).exists(),
             linimasa_mundur, bayar_mundur),
            (True,) * 7)

    def test_9_pengingat_servis_berkala_motor_dan_mobil_pelanggan1(self):
        p1 = Pelanggan.objects.get(user__username="pelanggan1")
        perlu = {type(k.spesifik()) for k in Kendaraan.objects.filter(pelanggan=p1) if k.perlu_servis_berkala}
        self.assertEqual(perlu, {Mobil, Motor})

    def test_10_mekanik3_cuti_dan_kasir2_nonaktif(self):
        self.assertEqual(
            (Mekanik.objects.get(user__username="mekanik3").status, User.objects.get(username="kasir2").is_active),
            (Mekanik.STATUS_CUTI, False))

    def test_11_badge_menyala(self):
        harap = {
            "kasir1": ["jumlah_pengajuan_menunggu", "jumlah_perlu_tindakan", "jumlah_bukti_menunggu", "jumlah_stok_kritis"],
            "admin1": ["jumlah_bukti_menunggu", "jumlah_stok_kritis", "jumlah_pembelian_draf"],
            "mekanik1": ["jumlah_stok_kritis"],
            "mekanik2": ["jumlah_panggilan_hs", "jumlah_perlu_dilihat"],
            "pelanggan1": ["jumlah_menunggu_persetujuan", "jumlah_kabar_riwayat"],
            "pelanggan2": ["jumlah_pengajuan_ditolak"],
        }
        padam = {u: [n for n in nama if not self.badge(u).get(n)] for u, nama in harap.items()}
        self.assertEqual(padam, {u: [] for u in harap})

    def test_12_ada_mekanik_tersedia_tanpa_pekerjaan_di_form_home_service(self):
        bebas = Mekanik.objects.filter(status=Mekanik.STATUS_TERSEDIA, transaksi_servis__isnull=True)
        self.assertTrue(bebas.exists())
        self.client.force_login(User.objects.get(username="pelanggan1"))
        halaman = self.client.get(reverse("pesan_home_service"))
        self.assertIn(bebas.first(), halaman.context["form"].fields["mekanik"].queryset)

    def test_13_badge_riwayat_pelanggan1_wajar(self):
        self.assertTrue(1 <= self.badge("pelanggan1")["jumlah_kabar_riwayat"] <= 3)


@override_settings(BUKTI_BAYAR_ROOT=Path(TMP))
class ResetBerulang(TestCase):
    def ringkas(self):
        return (T.objects.filter(keluhan__startswith="[DEMO] ").count(),
                PengajuanServis.objects.filter(keluhan__startswith="[DEMO] ").count(),
                Pembayaran.objects.count(), BuktiPembayaran.objects.count(), User.objects.count(),
                sum(1 for p in Path(TMP).rglob("*") if p.is_file()))

    def test_reset_dua_kali_sama_dan_data_web_tidak_tersentuh(self):
        seed()
        web = User.objects.create_user(username="budi_web", password="x", role=User.ROLE_PELANGGAN)
        motor = Motor.objects.create(pelanggan=Pelanggan.objects.create(user=web), no_polisi="KT 99 W",
                                     merk="Honda", model_kendaraan="Supra", tahun=2015, jenis_motor="Bebek",
                                     kapasitas_mesin=100)
        dari_web = T.buka(keterangan="Dari web", pelanggan=motor.pelanggan, kendaraan=motor, keluhan="Rem")
        pertama = self.ringkas()
        seed(reset=True)
        kedua = self.ringkas()
        seed(reset=True)
        self.assertEqual((kedua, self.ringkas()), (pertama, pertama))
        self.assertTrue(T.objects.filter(pk=dari_web.pk).exists())
        self.assertIsNone(User.objects.get(username="budi_web").alamat_lat)
