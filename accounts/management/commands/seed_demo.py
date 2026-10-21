"""
Isi database dengan data contoh untuk pengembangan & demo.

    python manage.py seed_demo            # tambah data (aman dijalankan berulang)
    python manage.py seed_demo --reset    # hapus transaksi demo lalu isi ulang (stok dikembalikan)

Di laptop, semua akun demo memakai kata sandi: demo12345

Di server (DEBUG mati), kata sandi itu tertulis di repo publik, jadi tidak
dipakai. Kata sandinya diberikan lewat environment variable:

    DJANGO_SANDI_DEMO='kata-sandi-pilihan' python manage.py seed_demo

Kata sandi itu berlaku untuk semua akun demo yang BARU dibuat. Akun yang
sudah ada, beserta kata sandinya, tidak disentuh.
Akun superuser asli TIDAK disentuh.
"""
import os

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Mekanik, Pelanggan, User
from kendaraan.models import Mobil, Motor, Truk
from mekanik.models import JenisServis
from servis.models import TransaksiServis as T
from sparepart.models import Sparepart

PASSWORD = "demo12345"
TANDA = "[DEMO] "  # awalan keluhan, dipakai untuk mengenali transaksi demo

AKUN = [
    # username, role, nama depan, spesialisasi
    ("admin1", User.ROLE_ADMIN, "Admin", ""),
    ("kasir1", User.ROLE_KASIR, "Kasir", ""),
    ("mekanik1", User.ROLE_MEKANIK, "Budi", "Mesin"),
    ("mekanik2", User.ROLE_MEKANIK, "Andi", "Kelistrikan"),
    ("pelanggan1", User.ROLE_PELANGGAN, "Siti", ""),
    ("pelanggan2", User.ROLE_PELANGGAN, "Joko", ""),
]

JENIS_SERVIS = [
    ("Ganti Oli", "Penggantian oli mesin", 30, 50000),
    ("Tune Up", "Penyetelan mesin menyeluruh", 90, 150000),
    ("Servis Rem", "Pemeriksaan dan penyetelan rem", 60, 100000),
    ("Servis AC", "Pembersihan dan isi ulang freon AC", 120, 250000),
    ("Ganti Ban", "Pemasangan dan balancing ban", 45, 75000),
]

# kode, nama, kategori, harga, stok awal, stok minimum
SPAREPART = [
    ("SP-001", "Oli Mesin 1L", "Oli", 60000, 40, 10),
    ("SP-002", "Kampas Rem Depan", "Rem", 80000, 25, 5),
    ("SP-003", "Filter Udara", "Filter", 45000, 20, 5),
    ("SP-004", "Busi", "Mesin", 25000, 60, 15),
    ("SP-005", "Aki 12V", "Kelistrikan", 550000, 3, 5),  # sengaja kritis: untuk menguji peringatan stok
    ("SP-006", "Ban Tubeless", "Ban", 320000, 12, 4),
]


class Command(BaseCommand):
    help = "Isi database dengan data demo (akun semua role, kendaraan, sparepart, transaksi berbagai status)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Hapus transaksi demo dan kembalikan stok sparepart sebelum mengisi ulang.")
        parser.add_argument("--izinkan-di-server", action="store_true",
                            help="Khusus tes otomatis: jalan walau DEBUG mati dengan sandi demo12345. "
                                 "Di server, pakai DJANGO_SANDI_DEMO.")

    @transaction.atomic
    def handle(self, *args, **opts):
        self.sandi = self._tentukan_sandi(opts)
        if opts["reset"]:
            demo = T.objects.filter(keluhan__startswith=TANDA)
            # Pembayaran memakai on_delete=PROTECT, jadi hapus pembayaran demo dulu
            from pembayaran.models import Pembayaran
            Pembayaran.objects.filter(transaksi__in=demo).delete()
            n, _ = demo.delete()
            self.stdout.write(f"Reset: {n} baris transaksi demo dihapus.")

        akun = self._buat_akun()
        jenis = self._buat_jenis_servis()
        sparepart = self._buat_sparepart(reset_stok=opts["reset"])
        kendaraan = self._buat_kendaraan(akun)

        if T.objects.filter(keluhan__startswith=TANDA).exists():
            self.stdout.write(self.style.WARNING(
                "Transaksi demo sudah ada, dilewati. Jalankan dengan --reset untuk mengisi ulang."))
        else:
            self._buat_transaksi(akun, jenis, sparepart, kendaraan)

        for m in Mekanik.objects.all():
            m.perbarui_status_otomatis()

        self.stdout.write(self.style.SUCCESS("\nSeed demo selesai."))
        if self.sandi == PASSWORD:
            self.stdout.write("Login (kata sandi semua akun demo: %s):" % PASSWORD)
        else:
            # Sandi dari environment sengaja tidak dicetak: log server bisa
            # dibaca orang lain.
            self.stdout.write("Login (kata sandi: nilai DJANGO_SANDI_DEMO, untuk akun yang baru dibuat):")
        for username, role, *_ in AKUN:
            self.stdout.write(f"  {username:<11} {role}")

    # ------------------------------------------------------------------
    def _tentukan_sandi(self, opts):
        """Kata sandi untuk akun demo yang baru dibuat.

        demo12345 tertulis di berkas ini, dan repo-nya publik. Di server yang
        bisa diakses siapa saja, memakainya sama dengan memberi kunci admin1
        ke semua orang. Jadi saat DEBUG mati (tanda server sungguhan), kata
        sandinya wajib datang dari DJANGO_SANDI_DEMO, dan harus lolos aturan
        kata sandi Django yang sama dengan akun biasa.
        """
        dari_env = os.environ.get("DJANGO_SANDI_DEMO", "")
        if dari_env:
            if dari_env == PASSWORD:
                raise CommandError(
                    f"DJANGO_SANDI_DEMO tidak boleh '{PASSWORD}': kata sandi itu "
                    "tertulis di repo publik."
                )
            try:
                validate_password(dari_env)
            except ValidationError as e:
                raise CommandError(
                    "DJANGO_SANDI_DEMO terlalu lemah: " + " ".join(e.messages)
                ) from e
            return dari_env

        if settings.DEBUG or opts["izinkan_di_server"]:
            return PASSWORD

        raise CommandError(
            "seed_demo menolak berjalan dengan kata sandi bawaan karena DEBUG "
            f"mati (tanda server sungguhan): '{PASSWORD}' tertulis di repo "
            "publik, termasuk untuk akun admin1. Berikan kata sandi sendiri:\n\n"
            "    DJANGO_SANDI_DEMO='kata-sandi-pilihan' python manage.py seed_demo\n"
        )

    def _buat_akun(self):
        hasil = {}
        for username, role, nama, spesialisasi in AKUN:
            user, baru = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": nama, "email": f"{username}@demo.local"},
            )
            if baru:
                user.set_password(self.sandi)
                user.save()
            if role == User.ROLE_MEKANIK:
                Mekanik.objects.get_or_create(user=user, defaults={"spesialisasi": spesialisasi})
            if role == User.ROLE_PELANGGAN:
                Pelanggan.objects.get_or_create(
                    user=user)
            hasil[username] = user
        return hasil

    def _buat_jenis_servis(self):
        return {
            nama: JenisServis.objects.get_or_create(
                nama_servis=nama,
                defaults={"deskripsi": desk, "estimasi_waktu": menit, "harga": harga})[0]
            for nama, desk, menit, harga in JENIS_SERVIS
        }

    def _buat_sparepart(self, reset_stok):
        hasil = {}
        for kode, nama, kategori, harga, stok, minimum in SPAREPART:
            sp, baru = Sparepart.objects.get_or_create(
                kode=kode,
                defaults={"nama": nama, "kategori": kategori, "harga": harga, "stok": stok, "stok_minimum": minimum})
            if reset_stok and not baru:
                sp.stok, sp.harga, sp.stok_minimum = stok, harga, minimum
                sp.save()
            hasil[kode] = sp
        return hasil

    def _buat_kendaraan(self, akun):
        p1 = akun["pelanggan1"].profil_pelanggan
        p2 = akun["pelanggan2"].profil_pelanggan
        data = {}
        data["mobil1"] = Mobil.objects.get_or_create(
            no_polisi="KT 1001 AA", defaults=dict(pelanggan=p1, merk="Toyota", model_kendaraan="Avanza", tahun=2020,
                                                  jumlah_pintu=4, jenis_mobil="MPV"))[0]
        data["motor1"] = Motor.objects.get_or_create(
            no_polisi="KT 2002 BB", defaults=dict(pelanggan=p1, merk="Honda", model_kendaraan="Beat", tahun=2021,
                                                  jenis_motor="Matic", kapasitas_mesin=110))[0]
        data["truk1"] = Truk.objects.get_or_create(
            no_polisi="KT 3003 CC", defaults=dict(pelanggan=p1, merk="Mitsubishi", model_kendaraan="Colt Diesel",
                                                  tahun=2018, kapasitas_muatan_kg=4000, jumlah_sumbu=2))[0]
        data["mobil2"] = Mobil.objects.get_or_create(
            no_polisi="KT 4004 DD", defaults=dict(pelanggan=p2, merk="Honda", model_kendaraan="Brio", tahun=2022,
                                                  jumlah_pintu=4, jenis_mobil="Hatchback"))[0]
        return data

    # ------------------------------------------------------------------
    def _buat_transaksi(self, akun, jenis, sp, kend):
        p1 = akun["pelanggan1"].profil_pelanggan
        p2 = akun["pelanggan2"].profil_pelanggan
        m1 = akun["mekanik1"].profil_mekanik
        m2 = akun["mekanik2"].profil_mekanik

        # Transaksi demo sengaja dibuat lewat method asli, bukan lewat kwarg.
        # Dua alasannya:
        #
        # 1. Linimasa FR-32 diisi oleh method-method itu sendiri. Transaksi
        #    yang mekaniknya dipasang lewat kwarg mekanik=... melompati
        #    ambil_oleh(), jadi tahap Pemeriksaan tidak pernah tercatat dan
        #    saat demo kartu "Perkembangan Servis" terlihat bolong: sebuah
        #    servis berstatus Selesai yang ceritanya baru mulai di
        #    "Persetujuan".
        # 2. Data demo yang menempuh alur asli sekalian membuktikan alurnya
        #    jalan. Kalau salah satu method menolak, seed_demo gagal keras,
        #    bukan diam-diam menghasilkan data yang tidak mungkin terjadi.
        #
        # kendaraan_hadir default True, jadi harus dimatikan dulu supaya
        # tandai_kendaraan_tiba() punya sesuatu untuk ditandai. Waktunya tetap
        # jujur: semuanya tercatat pada detik seed dijalankan, tidak dikarang
        # mundur.

        #
        # Transaksi juga dibuat lewat T.buka(), pintu yang sama dengan web,
        # jadi aturan satu kendaraan satu pekerjaan ikut berlaku di sini.
        # Data demo lama melanggarnya: Brio punya home service DAN servis
        # bengkel yang berjalan bersamaan, keadaan yang tidak mungkin dibuat
        # lewat web.

        def baru(pelanggan, kendaraan, keluhan, **kw):
            try:
                return T.buka(
                    keterangan="Permintaan servis dicatat petugas.",
                    pelanggan=pelanggan, kendaraan=kendaraan,
                    keluhan=TANDA + keluhan, **kw)
            except ValidationError as e:
                # handle() atomic, jadi reset di atas ikut dibatalkan dan
                # database kembali persis seperti sebelum perintah dijalankan.
                raise CommandError(
                    f"{kendaraan.no_polisi}: {' '.join(e.messages)} "
                    "Pekerjaan itu bukan data demo (dibuat lewat web), jadi "
                    "tidak dihapus --reset. Selesaikan atau batalkan dulu "
                    "lewat web, lalu jalankan ulang. Database tidak berubah."
                ) from e

        def tiba_di_bengkel(pelanggan, kendaraan, keluhan, mekanik=None):
            """Permintaan -> Kedatangan -> (Pemeriksaan)."""
            t = baru(pelanggan, kendaraan, keluhan, kendaraan_hadir=False)
            t.tandai_kendaraan_tiba()
            if mekanik is not None:
                t.ambil_oleh(mekanik)
                t.save()
            return t

        def sampai_dikerjakan(t):
            t.input_diagnosis("Hasil pemeriksaan: perlu perawatan berkala.", "Ganti oli dan periksa komponen terkait.")
            t.konfirmasi(True)

        # Urutannya mengikuti waktu sungguhan: dua transaksi yang sudah
        # TUNTAS dibuat dulu, baru empat yang masih berjalan. Satu kendaraan
        # hanya boleh punya satu pekerjaan berjalan, jadi Beat baru boleh
        # antri lagi setelah servis sebelumnya selesai, dan Colt Diesel baru
        # boleh dikerjakan setelah servis sebelumnya dibatalkan.

        # SELESAI: lengkap, bahan untuk nota & laporan.
        #   Ini transaksi contoh untuk memperlihatkan linimasa yang utuh:
        #   Permintaan, Kedatangan, Pemeriksaan, Persetujuan, Perbaikan, Selesai.
        t = tiba_di_bengkel(p1, kend["motor1"], "Servis rutin motor", mekanik=m1)
        sampai_dikerjakan(t)
        t.tambah_layanan(jenis["Tune Up"])
        t.tambah_layanan(jenis["Ganti Oli"])
        t.tambah_sparepart(sp["SP-004"], 2)
        t.tambah_sparepart(sp["SP-001"], 1)
        t.selesaikan()

        # DIBATALKAN: pelanggan menolak diagnosis
        t = tiba_di_bengkel(p1, kend["truk1"], "Truk susah starter", mekanik=m1)
        t.input_diagnosis("Aki lemah.", "Ganti aki baru.")
        t.konfirmasi(False)

        # MENUNGGU: antrian bengkel, belum diambil mekanik
        tiba_di_bengkel(p1, kend["motor1"], "Mesin kasar saat idle")

        # MENUNGGU_KONFIRMASI_MEKANIK: home service menunggu mekanik menerima
        baru(p2, kend["mobil2"], "Mobil mogok di rumah", mekanik=m2, tipe_layanan=T.TIPE_HOME_SERVICE,
             lokasi_servis="Jl. Pelita No. 12, Samarinda", status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
             kendaraan_hadir=False)

        # MENUNGGU_KONFIRMASI: sudah didiagnosis, menunggu persetujuan pelanggan
        t = tiba_di_bengkel(p1, kend["mobil1"], "Rem berdecit", mekanik=m1)
        t.input_diagnosis("Kampas rem depan menipis.", "Ganti kampas rem depan dan servis rem.")

        # DIKERJAKAN: ada layanan & sparepart. Dulu memakai Brio, yang
        # bersamaan sedang menunggu home service di atas.
        t = tiba_di_bengkel(p1, kend["truk1"], "Ganti oli dan tune up", mekanik=m2)
        sampai_dikerjakan(t)
        t.tambah_layanan(jenis["Ganti Oli"])
        t.tambah_sparepart(sp["SP-001"], 3)

        self.stdout.write("Transaksi demo: 6 transaksi (satu per status) dibuat.")
