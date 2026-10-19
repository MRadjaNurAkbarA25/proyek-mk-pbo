"""FR-11 + FR-31: kasir membuat transaksi di meja — pintu ketiga.

Aturan "satu kendaraan, satu pekerjaan berjalan" sudah dijaga di dua pintu:
Ajukan Servis dan Home Service. Pintu ketiga, kasir yang membuat transaksi
langsung di meja, dulu tidak memeriksa apa pun. Kasir bisa membuat
transaksi kedua untuk motor yang sedang dikerjakan mekanik, atau untuk
motor yang pengajuannya masih menunggu di daftar kasir sendiri.

Pintu ini juga satu-satunya yang tidak menulis baris pertama linimasa
FR-32, jadi linimasa transaksi buatan kasir langsung mulai di
"Pemeriksaan".

Tes di sini lewat HTTP, persis seperti kasir memakai web, supaya yang
diuji memang jalurnya, bukan cuma method-nya.
"""
from django.test import TestCase

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Motor
from servis.models import PembaruanServis, PengajuanServis, TransaksiServis

URL_BUAT = "/kasir/transaksi/buat/"


class DasarBuatTransaksi(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi", password="demo12345", role=User.ROLE_PELANGGAN)
        self.pelanggan = Pelanggan.objects.create(user=self.user)
        self.kasir = User.objects.create_user(
            username="kasir9", password="demo12345", role=User.ROLE_KASIR)
        mek_user = User.objects.create_user(
            username="mek9", password="demo12345", role=User.ROLE_MEKANIK)
        self.mekanik = Mekanik.objects.create(
            user=mek_user, status=Mekanik.STATUS_TERSEDIA)
        self.motor = Motor.objects.create(
            pelanggan=self.pelanggan, no_polisi="KT 1234 ZZ",
            merk="Honda", model_kendaraan="Beat", tahun=2020,
            jenis_motor="Matic", kapasitas_mesin=110)

    def kasir_buat(self, keluhan="Rem bunyi"):
        self.client.force_login(self.kasir)
        return self.client.post(URL_BUAT, {
            "no_polisi": self.motor.no_polisi, "keluhan": keluhan,
        })


class KasirTidakBisaMembuatPekerjaanKedua(DasarBuatTransaksi):
    def test_ditolak_kalau_kendaraan_sedang_diservis(self):
        self.assertEqual(self.kasir_buat().status_code, 302)
        self.assertEqual(TransaksiServis.objects.count(), 1)

        respons = self.kasir_buat("Keluhan lain")
        self.assertEqual(respons.status_code, 200, "transaksi kedua seharusnya ditolak")
        self.assertContains(respons, "masih dalam proses servis")
        self.assertEqual(TransaksiServis.objects.count(), 1)

    def test_ditolak_kalau_ada_home_service_berjalan(self):
        self.client.force_login(self.user)
        self.client.post("/pelanggan/home-service/pesan/", {
            "kendaraan": f"motor:{self.motor.pk}",
            "mekanik": str(self.mekanik.pk),
            "keluhan": "Mesin tidak mau hidup",
            "lokasi_servis": "Jl. Mawar No. 10, Samarinda",
        })
        self.assertEqual(TransaksiServis.objects.count(), 1)

        respons = self.kasir_buat()
        self.assertContains(respons, "masih dalam proses servis")
        self.assertEqual(TransaksiServis.objects.count(), 1)

    def test_ditolak_kalau_pengajuannya_masih_menunggu(self):
        """Kasir harus memproses pengajuannya, bukan membuat transaksi kembar."""
        PengajuanServis.objects.create(
            pelanggan=self.pelanggan, kendaraan=self.motor, keluhan="Oli bocor")

        respons = self.kasir_buat()
        self.assertContains(respons, "menunggu persetujuan kasir")
        self.assertEqual(TransaksiServis.objects.count(), 0)

    def test_boleh_lagi_setelah_servis_sebelumnya_selesai(self):
        self.kasir_buat()
        TransaksiServis.objects.update(status=TransaksiServis.STATUS_SELESAI)

        self.assertEqual(self.kasir_buat("Servis rutin").status_code, 302)
        self.assertEqual(TransaksiServis.objects.count(), 2)


class LinimasaTransaksiKasirTidakBolong(DasarBuatTransaksi):
    def test_baris_pertama_adalah_permintaan(self):
        self.kasir_buat()
        transaksi = TransaksiServis.objects.get()

        pertama = transaksi.pembaruan.first()
        self.assertIsNotNone(pertama, "transaksi buatan kasir harus punya linimasa")
        self.assertEqual(pertama.tahap, PembaruanServis.TAHAP_PERMINTAAN)
        self.assertEqual(pertama.oleh, self.kasir)

    def test_alur_lengkap_dari_meja_kasir_berurutan(self):
        self.kasir_buat()
        transaksi = TransaksiServis.objects.get()
        transaksi.ambil_oleh(self.mekanik)
        transaksi.save()
        transaksi.input_diagnosis("Kampas aus", "Ganti kampas rem")
        transaksi.konfirmasi(True)
        transaksi.selesaikan()

        self.assertEqual([p.tahap for p in transaksi.pembaruan.all()], [
            PembaruanServis.TAHAP_PERMINTAAN,
            PembaruanServis.TAHAP_PEMERIKSAAN,
            PembaruanServis.TAHAP_PERSETUJUAN,
            PembaruanServis.TAHAP_PERBAIKAN,
            PembaruanServis.TAHAP_SELESAI,
        ])


class KasirMelihatLinimasa(DasarBuatTransaksi):
    """FR-32: kasir yang ditelepon pelanggan melihat cerita yang sama."""

    def test_detail_transaksi_menampilkan_kabar_mekanik(self):
        self.kasir_buat()
        t = TransaksiServis.objects.get()
        t.ambil_oleh(self.mekanik)
        t.save()
        t.input_diagnosis("Kampas aus", "Ganti kampas")
        t.konfirmasi(True)
        t.tulis_pembaruan(self.mekanik, "Menunggu kampas datang besok pagi.")

        respons = self.client.get(f"/kasir/transaksi/{t.pk}/")
        self.assertContains(respons, "Perkembangan Servis")
        self.assertContains(respons, "Kendaraan diterima di bengkel dan didaftarkan kasir.")
        self.assertContains(respons, "Menunggu kampas datang besok pagi.")
        self.assertContains(respons, "css/linimasa.css")


class KetigaPintuMelewatiSatuMethod(DasarBuatTransaksi):
    """Penjaga struktur: aturan dan baris pertama linimasa ada di SATU tempat.

    Dua lubang di atas terjadi karena tiap pintu membuat transaksinya
    sendiri-sendiri lewat objects.create() dan harus ingat memanggil
    pemeriksaan serta pencatat. Kalau suatu saat ada yang kembali menulis
    objects.create() langsung di view, tes ini yang merah.
    """

    def test_tidak_ada_view_yang_membuat_transaksi_langsung(self):
        import pathlib
        import re

        akar = pathlib.Path(__file__).resolve().parent.parent
        pelanggar = []
        for berkas in akar.rglob("*.py"):
            bagian = berkas.relative_to(akar).parts
            if (bagian[0] in {"venv", ".venv", "staticfiles"}
                    or "migrations" in bagian
                    or berkas.name.startswith("test")
                    or bagian == ("servis", "models.py")):
                continue
            teks = berkas.read_text(encoding="utf-8")
            if re.search(r"TransaksiServis\.objects\.create\(", teks):
                pelanggar.append(str(berkas.relative_to(akar)))

        self.assertEqual(
            pelanggar, [],
            "Buat transaksi lewat TransaksiServis.buka(), bukan objects.create(), "
            "supaya aturan satu kendaraan dan linimasa tidak terlewat.",
        )
