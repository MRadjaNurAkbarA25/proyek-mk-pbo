"""Isi database dengan data contoh: `seed_demo` (aman diulang), `seed_demo --reset`.

Di laptop sandinya demo12345; di server (DEBUG mati) wajib DJANGO_SANDI_DEMO.
Akun yang sudah ada dan superuser tidak disentuh.
"""
import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from accounts.models import Mekanik, Pelanggan, User
from faq.data_awal import isi_faq_awal
from kendaraan.models import Mobil, Motor
from mekanik.models import JenisServis
from pembayaran.models import BuktiPembayaran, Pembayaran
from pembelian.models import DetailPembelian, PembelianSparepart, Supplier
from servis.models import PembaruanServis, PengajuanServis
from servis.models import TransaksiServis as T
from sparepart.models import Sparepart

# PNG 1x1 transparan, untuk contoh bukti pembayaran.
PNG_CONTOH = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000100e221bc330000000049454e44ae426082")

PASSWORD = "demo12345"
TANDA = "[DEMO] "  # awalan keluhan, dipakai untuk mengenali transaksi dan pengajuan demo

AKUN = [
    # username, role, nama depan, spesialisasi, yang bisa diperagakan
    ("admin1", User.ROLE_ADMIN, "Admin", "", "laporan, verifikasi bayar, stok kritis, pembelian draf"),
    ("kasir1", User.ROLE_KASIR, "Kasir", "", "pengajuan menunggu, perlu tindakan, verifikasi bukti"),
    ("kasir2", User.ROLE_KASIR, "Dewi", "", "akun nonaktif (tidak bisa login)"),
    ("mekanik1", User.ROLE_MEKANIK, "Budi", "Mesin", "home service di lokasi: Pelanggan setuju di lokasi"),
    ("mekanik2", User.ROLE_MEKANIK, "Andi", "Kelistrikan", "panggilan home service baru, pesan pelanggan"),
    ("mekanik3", User.ROLE_MEKANIK, "Rudi", "Ban & Kaki-kaki", "status Cuti (tidak bisa dipanggil)"),
    ("mekanik4", User.ROLE_MEKANIK, "Dedi", "Servis Ringan", "Tersedia tanpa pekerjaan (bisa dipesan Home Service)"),
    ("pelanggan1", User.ROLE_PELANGGAN, "Siti", "", "persetujuan diagnosis, peta, pengingat servis"),
    ("pelanggan2", User.ROLE_PELANGGAN, "Joko", "", "pengajuan ditolak, tagihan belum dibayar"),
    ("pelanggan3", User.ROLE_PELANGGAN, "Rina", "", "belum punya kendaraan (instruksi tambah)"),
]

# Alamat dan titik contoh di sekitar bengkel; bukan alamat rumah siapa pun.
ALAMAT_CONTOH = "Jl. Pramuka (alamat contoh), Samarinda"
TITIK_CONTOH = (Decimal("-0.462500"), Decimal("117.150800"))
LOKASI_HS = [
    ("Area parkir Jl. Juanda (lokasi contoh), Samarinda", Decimal("-0.471200"), Decimal("117.163400")),
    ("Halaman kantor Jl. Pramuka (lokasi contoh), Samarinda", Decimal("-0.462500"), Decimal("117.150800")),
    ("Jl. Sempaja (lokasi contoh), Samarinda", Decimal("-0.455300"), Decimal("117.159100")),
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

# nama, telepon, alamat
SUPPLIER = [
    ("PT Sinar Jaya Sparepart", "0812-3456-7890", "Jl. Pahlawan No. 12, Samarinda"),
    ("CV Maju Bersama", "0821-9876-5432", "Jl. Gajah Mada No. 45, Balikpapan"),
    ("UD Borneo Motor Parts", "0813-5000-2211", "Jl. Juanda No. 8, Samarinda"),
]

# kunci, pemilik, kelas, no polisi, merk, model, tahun pembuatan, data subkelas
KENDARAAN = [
    ("mobil1", "pelanggan1", Mobil, "KT 1001 AA", "Toyota", "Avanza", 2020, dict(jumlah_pintu=4, jenis_mobil="MPV")),
    ("motor1", "pelanggan1", Motor, "KT 2002 BB", "Honda", "Beat", 2021, dict(jenis_motor="Matic", kapasitas_mesin=110)),
    # Nomor polisi ini dipertahankan: migrasi kendaraan 0002 mengubah data
    # lama menjadi Mobil bernomor sama, jadi get_or_create menemukannya.
    ("mobil3", "pelanggan1", Mobil, "KT 3003 CC", "Mitsubishi", "L300", 2018, dict(jumlah_pintu=2, jenis_mobil="Pick-up")),
    ("mobil2", "pelanggan2", Mobil, "KT 4004 DD", "Honda", "Brio", 2022, dict(jumlah_pintu=4, jenis_mobil="Hatchback")),
    ("motor2", "pelanggan2", Motor, "KT 5005 EE", "Yamaha", "Mio", 2019, dict(jenis_motor="Matic", kapasitas_mesin=125)),
    ("mobil4", "pelanggan2", Mobil, "KT 6006 FF", "Suzuki", "Ertiga", 2021, dict(jumlah_pintu=4, jenis_mobil="MPV")),
    ("motor3", "pelanggan1", Motor, "KT 7007 GG", "Yamaha", "NMAX", 2022, dict(jenis_motor="Matic", kapasitas_mesin=155)),
    ("motor4", "pelanggan1", Motor, "KT 8008 HH", "Honda", "Vario", 2019, dict(jenis_motor="Matic", kapasitas_mesin=125)),
    ("mobil5", "pelanggan1", Mobil, "KT 9009 II", "Daihatsu", "Xenia", 2017, dict(jumlah_pintu=4, jenis_mobil="MPV")),
]


class Command(BaseCommand):
    help = "Isi database dengan data demo (akun semua role, kendaraan, sparepart, transaksi berbagai status)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Hapus transaksi dan pengajuan demo, kembalikan stok sparepart, lalu isi ulang.")
        parser.add_argument("--izinkan-di-server", action="store_true",
                            help="Khusus tes otomatis: jalan walau DEBUG mati dengan sandi demo12345. "
                                 "Di server, pakai DJANGO_SANDI_DEMO.")

    @transaction.atomic
    def handle(self, *args, **opts):
        self.sandi = self._tentukan_sandi(opts)
        if opts["reset"]:
            self._hapus_demo()

        akun = self._buat_akun()
        jenis = self._buat_jenis_servis()
        sparepart = self._buat_sparepart(reset_stok=opts["reset"])
        supplier = self._buat_supplier()
        self._buat_pembelian(supplier, sparepart)
        kendaraan = self._buat_kendaraan(akun)

        # FR-34: FAQ chat. Hanya menambah yang belum ada, tidak menimpa hasil
        # suntingan admin, dan tidak tersentuh --reset.
        faq_baru = isi_faq_awal()
        self.stdout.write(f"FAQ chat: {faq_baru} pertanyaan baru ditambahkan.")

        if T.objects.filter(keluhan__startswith=TANDA).exists():
            self.stdout.write(self.style.WARNING(
                "Transaksi demo sudah ada, dilewati. Jalankan dengan --reset untuk mengisi ulang."))
        else:
            # Status mekanik disegarkan dulu: --reset bisa meninggalkan "Sedang Servis" basi.
            for m in Mekanik.objects.all():
                m.perbarui_status_otomatis()
            self._buat_transaksi(akun, jenis, sparepart, kendaraan)

        for m in Mekanik.objects.all():
            m.perbarui_status_otomatis()
        self._atur_status_akun(akun)

        self.stdout.write(self.style.SUCCESS("\nSeed demo selesai."))
        if self.sandi == PASSWORD:
            self.stdout.write("Login (kata sandi semua akun demo: %s):" % PASSWORD)
        else:
            # Sandi dari environment sengaja tidak dicetak: log server bisa
            # dibaca orang lain.
            self.stdout.write("Login (kata sandi: nilai DJANGO_SANDI_DEMO, untuk akun yang baru dibuat):")
        for username, role, _, _, peragaan in AKUN:
            self.stdout.write(f"  {username:<11} {role:<10} {peragaan}")

    # ------------------------------------------------------------------
    def _hapus_demo(self):
        demo = T.objects.filter(keluhan__startswith=TANDA)
        n_pengajuan, _ = PengajuanServis.objects.filter(keluhan__startswith=TANDA).delete()
        # Pembayaran dan bukti memakai on_delete=PROTECT, jadi dihapus dulu.
        Pembayaran.objects.filter(transaksi__in=demo).delete()
        for bukti in BuktiPembayaran.objects.filter(transaksi__in=demo):
            bukti.berkas.delete(save=False)  # berkas di folder privat ikut dihapus
            bukti.delete()
        n, _ = demo.delete()
        self.stdout.write(f"Reset: {n} baris transaksi demo dan {n_pengajuan} pengajuan demo dihapus.")

    def _tentukan_sandi(self, opts):
        """Sandi akun demo baru: demo12345 tertulis di repo publik, jadi saat DEBUG mati
        wajib dari DJANGO_SANDI_DEMO dan harus lolos validator sandi Django.
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
        for username, role, nama, spesialisasi, _ in AKUN:
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
                Pelanggan.objects.get_or_create(user=user)
            hasil[username] = user

        # Profil pelanggan1 untuk Home Service yang terisi otomatis; hanya kalau titiknya belum ada.
        p1 = hasil["pelanggan1"]
        if p1.alamat_lat is None:
            p1.alamat = p1.alamat or ALAMAT_CONTOH
            p1.no_telepon = p1.no_telepon or "0812-0000-0001"
            p1.alamat_lat, p1.alamat_lng = TITIK_CONTOH
            p1.save(update_fields=["alamat", "no_telepon", "alamat_lat", "alamat_lng"])
        return hasil

    def _atur_status_akun(self, akun):
        """mekanik3 Cuti dan kasir2 nonaktif, lewat method yang sama dengan halaman web."""
        m3 = akun["mekanik3"].profil_mekanik
        m3.refresh_from_db()
        if m3.status != Mekanik.STATUS_CUTI:
            m3.ubah_ketersediaan(Mekanik.STATUS_CUTI)
        kasir2 = akun["kasir2"]
        kasir2.refresh_from_db()
        if kasir2.is_active:
            kasir2.nonaktifkan()

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
                # Stok hanya bertambah lewat pembelian, dan --reset tidak
                # menghapus pembelian. Jadi barang yang sudah dibeli tetap
                # dihitung: stok awal + semua pembelian yang selesai.
                dibeli = DetailPembelian.objects.filter(
                    sparepart=sp, pembelian__status=PembelianSparepart.STATUS_SELESAI,
                ).aggregate(n=Sum("jumlah"))["n"] or 0
                sp.stok, sp.harga, sp.stok_minimum = stok + dibeli, harga, minimum
                sp.save()
            hasil[kode] = sp
        return hasil

    def _buat_supplier(self):
        return {
            nama: Supplier.objects.get_or_create(
                nama=nama, defaults={"telepon": telepon, "alamat": alamat})[0]
            for nama, telepon, alamat in SUPPLIER
        }

    def _buat_pembelian(self, supplier, sparepart):
        """Satu pembelian SELESAI + satu DRAF, lewat method model supaya stok benar bertambah.

        Draf Aki sengaja belum diselesaikan agar Aki tetap kritis untuk contoh peringatan stok.
        """
        if PembelianSparepart.objects.filter(supplier__nama__in=[n for n, _, _ in SUPPLIER]).exists():
            self.stdout.write("Pembelian demo sudah ada, dilewati.")
            return

        admin1 = User.objects.get(username="admin1")

        selesai = PembelianSparepart.objects.create(
            supplier=supplier["PT Sinar Jaya Sparepart"],
            metode_bayar=PembelianSparepart.METODE_TRANSFER,
            dicatat_oleh=admin1,
        )
        selesai.tambah_barang(sparepart["SP-001"], 10, 52000)
        selesai.tambah_barang(sparepart["SP-004"], 15, 20000)
        selesai.selesaikan()

        draf = PembelianSparepart.objects.create(
            supplier=supplier["CV Maju Bersama"],
            metode_bayar=PembelianSparepart.METODE_TUNAI,
            dicatat_oleh=admin1,
        )
        draf.tambah_barang(sparepart["SP-005"], 4, 500000)

        self.stdout.write("Pembelian demo: 1 selesai + 1 draf dibuat.")

    def _buat_kendaraan(self, akun):
        data = {}
        for kunci, pemilik, Kelas, no_polisi, merk, model, tahun, lain in KENDARAAN:
            data[kunci] = Kelas.objects.get_or_create(
                no_polisi=no_polisi,
                defaults=dict(pelanggan=akun[pemilik].profil_pelanggan, merk=merk,
                              model_kendaraan=model, tahun=tahun, **lain))[0]
        return data

    # ------------------------------------------------------------------
    def _buat_transaksi(self, akun, jenis, sp, kend):
        p1 = akun["pelanggan1"].profil_pelanggan
        p2 = akun["pelanggan2"].profil_pelanggan
        m1 = akun["mekanik1"].profil_mekanik
        m2 = akun["mekanik2"].profil_mekanik
        kasir = akun["kasir1"]

        # Transaksi demo dibuat lewat method asli (bukan kwarg) supaya linimasa
        # FR-32 terisi lengkap dan alurnya ikut teruji: kalau method menolak,
        # seed_demo gagal keras. T.buka() menjaga aturan satu kendaraan satu pekerjaan.

        def baru(pelanggan, kendaraan, keluhan, keterangan="Permintaan servis dicatat petugas.", **kw):
            try:
                return T.buka(
                    keterangan=keterangan,
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

        def panggil(pelanggan, kendaraan, keluhan, mekanik, lokasi):
            alamat, lat, lng = lokasi
            return baru(pelanggan, kendaraan, keluhan,
                        keterangan=f"Panggilan home service dikirim ke mekanik {mekanik.user.nama_tampil}.",
                        mekanik=mekanik, tipe_layanan=T.TIPE_HOME_SERVICE, lokasi_servis=alamat,
                        lokasi_lat=lat, lokasi_lng=lng, status=T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
                        kendaraan_hadir=False)

        def tiba_di_bengkel(pelanggan, kendaraan, keluhan, mekanik=None):
            """Permintaan -> Kedatangan -> (Pemeriksaan)."""
            t = baru(pelanggan, kendaraan, keluhan, kendaraan_hadir=False)
            t.tandai_kendaraan_tiba()
            if mekanik is not None:
                t.ambil_oleh(mekanik)
                t.save()
            return t

        def sampai_dikerjakan(t, diagnosis="Hasil pemeriksaan: perlu perawatan berkala.",
                              rekomendasi="Ganti oli dan periksa komponen terkait."):
            t.input_diagnosis(diagnosis, rekomendasi)
            t.konfirmasi(True)
            t.tandai_dibaca_mekanik()  # mekanik membuka detail untuk mulai bekerja

        def kerjakan(t, layanan, barang=()):
            for nama in layanan:
                t.tambah_layanan(jenis[nama])
            for kode, jumlah in barang:
                t.tambah_sparepart(sp[kode], jumlah)
            t.selesaikan()

        # 1) Riwayat lunas, dibuat paling dulu selagi semua mekanik Tersedia.
        riwayat = [
            # hari lalu, pelanggan, kendaraan, keluhan, mekanik, layanan, sparepart, bayar
            (200, p1, "mobil5", "Servis rutin mobil", m1, ["Tune Up"], [("SP-003", 1)], "cash"),
            (85, p1, "motor4", "Ganti oli motor", m1, ["Ganti Oli"], [("SP-001", 1)], "cash"),
            (70, p1, "mobil1", "AC kurang dingin", m2, ["Servis AC"], [], "transfer"),
            (50, p2, "mobil2", "Rem mobil bunyi", m1, ["Servis Rem"], [("SP-002", 1)], "cash"),
            (15, p1, "motor1", "Ban bocor halus", m2, ["Ganti Ban"], [("SP-006", 1)], "cash"),
        ]
        for hari, pel, k, keluhan, mek, layanan, barang, bayar in riwayat:
            t = tiba_di_bengkel(pel, kend[k], keluhan, mekanik=mek)
            sampai_dikerjakan(t)
            kerjakan(t, layanan, barang)
            self._bayar(t, pel, kasir, bayar)
            self._mundurkan(t, hari)
            t.tandai_dibaca_pelanggan()

        # Home service yang dilanjutkan di bengkel (berawal_home_service).
        t = panggil(p2, kend["motor2"], "Motor tidak mau hidup", m2, LOKASI_HS[2])
        t.terima_home_service()
        sampai_dikerjakan(t, "Kompresi rendah, perlu dibongkar.", "Tune up menyeluruh di bengkel.")
        t.lanjutkan_di_bengkel(timezone.localdate() + timedelta(days=1))
        t.tandai_kendaraan_tiba()
        kerjakan(t, ["Tune Up"], [("SP-004", 1)])
        self._bayar(t, p2, kasir, "cash")
        self._mundurkan(t, 30)
        t.tandai_dibaca_pelanggan()

        # 2) Home service diterima mekanik1, berhenti di Menunggu Konfirmasi Pelanggan
        #    (peragaan "Pelanggan setuju di lokasi" dan tombol WhatsApp mekanik).
        #    Pelanggan ada di lokasi bersama mekanik, jadi kabarnya dianggap sudah dibaca.
        t = panggil(p1, kend["motor3"], "Motor mati mendadak di jalan", m1, LOKASI_HS[1])
        t.terima_home_service()
        t.input_diagnosis("Aki soak dan kabel busi longgar.", "Ganti aki dan kencangkan kabel busi.")
        t.tandai_dibaca_mekanik()
        t.tandai_dibaca_pelanggan()

        # 3) Transaksi berjalan. Badge Riwayat pelanggan1 hanya menyala untuk tiga yang
        #    memang baru: bukti ditolak, diagnosis menunggu, dan servis yang dikerjakan.
        # SELESAI: lengkap, bahan untuk nota & laporan; linimasa utuh 6 tahap.
        t = tiba_di_bengkel(p1, kend["motor1"], "Servis rutin motor", mekanik=m1)
        sampai_dikerjakan(t)
        kerjakan(t, ["Tune Up", "Ganti Oli"], [("SP-004", 2), ("SP-001", 1)])
        self._contoh_bukti(t, p1, kasir)

        # DIBATALKAN: pelanggan menolak diagnosis
        t = tiba_di_bengkel(p1, kend["mobil3"], "Mobil susah starter", mekanik=m1)
        t.input_diagnosis("Aki lemah.", "Ganti aki baru.")
        t.konfirmasi(False)
        t.tandai_dibaca_mekanik()
        t.tandai_dibaca_pelanggan()

        # MENUNGGU: antrian bengkel, belum diambil mekanik
        tiba_di_bengkel(p1, kend["motor1"], "Mesin kasar saat idle").tandai_dibaca_pelanggan()

        # MENUNGGU_KONFIRMASI_MEKANIK: panggilan home service baru untuk mekanik2.
        panggil(p2, kend["mobil2"], "Mobil mogok di depan kantor", m2, LOKASI_HS[0])

        # SELESAI + LUNAS tunai: contoh nota yang sudah bisa dibuka.
        t = tiba_di_bengkel(p1, kend["mobil1"], "Ganti oli mobil", mekanik=m1)
        sampai_dikerjakan(t)
        kerjakan(t, ["Ganti Oli"], [("SP-001", 4)])
        Pembayaran.catat_cash(t, t.total_biaya, oleh=kasir)
        t.tandai_dibaca_pelanggan()

        # MENUNGGU_KONFIRMASI: sudah didiagnosis, menunggu persetujuan pelanggan
        t = tiba_di_bengkel(p1, kend["mobil1"], "Rem berdecit", mekanik=m1)
        t.input_diagnosis("Kampas rem depan menipis.", "Ganti kampas rem depan dan servis rem.")

        # SELESAI belum dibayar, tanpa bukti: badge Daftar Transaksi kasir dan kartu tagihan pelanggan2.
        t = tiba_di_bengkel(p2, kend["motor2"], "Ganti oli motor", mekanik=m1)
        sampai_dikerjakan(t)
        kerjakan(t, ["Ganti Oli"], [("SP-001", 1)])

        # DIKERJAKAN: kabar mekanik lalu pertanyaan pelanggan (badge Pengerjaan mekanik2).
        t = tiba_di_bengkel(p1, kend["mobil3"], "Ganti oli dan tune up", mekanik=m2)
        sampai_dikerjakan(t)
        t.tambah_layanan(jenis["Ganti Oli"])
        t.tambah_sparepart(sp["SP-001"], 3)
        t.tulis_pembaruan(m2, "Oli sudah diganti, sekarang memeriksa filter udara.")
        t.refresh_from_db()
        t.tulis_pesan_pelanggan(p1, "Kira-kira mobilnya bisa diambil jam berapa?")

        # 4) Pengajuan servis pelanggan2: satu menunggu kasir, satu ditolak dan belum dilihat.
        PengajuanServis.objects.create(
            pelanggan=p2, kendaraan=kend["mobil4"], keluhan=TANDA + "AC mobil berbau apek",
            tanggal_rencana_datang=timezone.localdate() + timedelta(days=2))
        ditolak = PengajuanServis.objects.create(
            pelanggan=p2, kendaraan=kend["motor2"], keluhan=TANDA + "Minta cat ulang bodi motor")
        ditolak.tolak(kasir, "Bengkel kami belum melayani pengecatan bodi.")

        self.stdout.write(
            "Transaksi demo: riwayat 3 bulan (6 lunas), 2 home service, 8 transaksi berjalan/terbaru, "
            "2 pengajuan dibuat.")

    def _bayar(self, t, pelanggan, kasir, cara):
        if cara == "transfer":
            bukti = BuktiPembayaran.ajukan(
                t, pelanggan, jenis=BuktiPembayaran.JENIS_BANK, nama_penyedia="BRI",
                nomor_referensi=f"DEMO-TRF-LUNAS-{t.pk}",
                berkas=ContentFile(PNG_CONTOH, name="bukti-transfer-lunas.png"))
            bukti.setujui(kasir)
        else:
            Pembayaran.catat_cash(t, t.total_biaya, oleh=kasir)

    def _mundurkan(self, t, hari):
        """Khusus data demo: geser seluruh jejak transaksi ke `hari` yang lalu untuk riwayat dan laporan."""
        mundur = timedelta(days=hari)
        T.objects.filter(pk=t.pk).update(
            tanggal=F("tanggal") - mundur, tanggal_rencana_datang=F("tanggal_rencana_datang") - mundur)
        PembaruanServis.objects.filter(transaksi=t).update(waktu=F("waktu") - mundur)
        Pembayaran.objects.filter(transaksi=t).update(tanggal=F("tanggal") - mundur)
        BuktiPembayaran.objects.filter(transaksi=t).update(
            diunggah_pada=F("diunggah_pada") - mundur, diperiksa_pada=F("diperiksa_pada") - mundur)
        t.refresh_from_db()
        T.objects.filter(pk=t.pk).update(kode_transaksi=f"TRX-{timezone.localtime(t.tanggal):%Y%m%d}-{t.pk:05d}")

    def _contoh_bukti(self, t, pelanggan, kasir):
        """Bahan Verifikasi Pembayaran: satu bukti ditolak, satu menunggu (lewat ajukan()/tolak())."""

        def gambar(nama):
            return ContentFile(PNG_CONTOH, name=nama)

        ditolak = BuktiPembayaran.ajukan(
            t, pelanggan, jenis=BuktiPembayaran.JENIS_E_MONEY, nama_penyedia="QRIS",
            nomor_referensi=f"DEMO-QRIS-{t.pk}", berkas=gambar("bukti-qris.png"))
        ditolak.tolak(kasir, "Nominal di bukti tidak sesuai tagihan")
        BuktiPembayaran.ajukan(
            t, pelanggan, jenis=BuktiPembayaran.JENIS_BANK, nama_penyedia="BRI",
            nomor_referensi=f"DEMO-TRF-{t.pk}", berkas=gambar("bukti-transfer.png"))
        self.stdout.write("Bukti pembayaran demo: 1 ditolak + 1 menunggu verifikasi kasir.")
