"""
Isi database dengan data contoh untuk pengembangan & demo.

    python manage.py seed_demo            # tambah data (aman dijalankan berulang)
    python manage.py seed_demo --reset    # hapus transaksi demo lalu isi ulang (stok dikembalikan)

Semua akun demo memakai kata sandi: demo12345
Akun superuser asli TIDAK disentuh.
"""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
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

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            n, _ = T.objects.filter(keluhan__startswith=TANDA).delete()
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
        self.stdout.write("Login (kata sandi semua akun: %s):" % PASSWORD)
        for username, role, *_ in AKUN:
            self.stdout.write(f"  {username:<11} {role}")

    # ------------------------------------------------------------------
    def _buat_akun(self):
        hasil = {}
        for username, role, nama, spesialisasi in AKUN:
            user, baru = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": nama, "email": f"{username}@demo.local"},
            )
            if baru:
                user.set_password(PASSWORD)
                user.save()
            if role == User.ROLE_MEKANIK:
                Mekanik.objects.get_or_create(user=user, defaults={"spesialisasi": spesialisasi})
            if role == User.ROLE_PELANGGAN:
                Pelanggan.objects.get_or_create(
                    user=user, defaults={"no_telepon": "081200000000", "alamat": "Jl. Contoh No. 1, Samarinda"})
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

        def baru(pelanggan, kendaraan, keluhan, mekanik=None, **kw):
            return T.objects.create(pelanggan=pelanggan, kendaraan=kendaraan, mekanik=mekanik,
                                    keluhan=TANDA + keluhan, **kw)

        def sampai_dikerjakan(t):
            t.input_diagnosis("Hasil pemeriksaan: perlu perawatan berkala.", "Ganti oli dan periksa komponen terkait.")
            t.konfirmasi(True)

        # 1. MENUNGGU: antrian bengkel, belum diambil mekanik
        baru(p1, kend["motor1"], "Mesin kasar saat idle")

        # 2. MENUNGGU_KONFIRMASI_MEKANIK: home service menunggu mekanik menerima
        baru(p2, kend["mobil2"], "Mobil mogok di rumah", mekanik=m2, tipe_layanan=T.TIPE_HOME_SERVICE,
             lokasi_servis="Jl. Pelita No. 12, Samarinda", status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK)

        # 3. MENUNGGU_KONFIRMASI: sudah didiagnosis, menunggu persetujuan pelanggan
        t = baru(p1, kend["mobil1"], "Rem berdecit", mekanik=m1)
        t.input_diagnosis("Kampas rem depan menipis.", "Ganti kampas rem depan dan servis rem.")

        # 4. DIKERJAKAN: ada layanan & sparepart
        t = baru(p2, kend["mobil2"], "Ganti oli dan tune up", mekanik=m2)
        sampai_dikerjakan(t)
        t.tambah_layanan(jenis["Ganti Oli"])
        t.tambah_sparepart(sp["SP-001"], 3)

        # 5. SELESAI: lengkap, bahan untuk nota & laporan
        t = baru(p1, kend["motor1"], "Servis rutin motor", mekanik=m1)
        sampai_dikerjakan(t)
        t.tambah_layanan(jenis["Tune Up"])
        t.tambah_layanan(jenis["Ganti Oli"])
        t.tambah_sparepart(sp["SP-004"], 2)
        t.tambah_sparepart(sp["SP-001"], 1)
        t.selesaikan()

        # 6. DIBATALKAN: pelanggan menolak diagnosis
        t = baru(p1, kend["truk1"], "Truk susah starter", mekanik=m1)
        t.input_diagnosis("Aki lemah.", "Ganti aki baru.")
        t.konfirmasi(False)

        self.stdout.write("Transaksi demo: 6 transaksi (satu per status) dibuat.")
