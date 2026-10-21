from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from accounts.models import Pelanggan


class Kendaraan(models.Model):
    """Class induk: atribut yang dimiliki semua jenis kendaraan.

    Jenisnya dua, Mobil dan Motor, sesuai dokumen rancangan. Truk pernah
    ditambahkan di luar dokumen lalu dihapus; data truk lama dijadikan Mobil
    (migrasi kendaraan 0002).
    """

    #: Nama relasi ke setiap subkelas. SATU-SATUNYA tempat daftar ini ditulis:
    #: query yang perlu memuat subkelas sekaligus memakai relasi_subkelas(),
    #: dan spesifik() mencoba nama-nama ini satu per satu. Menambah jenis
    #: kendaraan cukup menambah satu nama di sini plus satu class baru.
    SUBKELAS = ("mobil", "motor")

    pelanggan = models.ForeignKey(
        Pelanggan, on_delete=models.CASCADE, related_name="daftar_kendaraan"
    )
    no_polisi = models.CharField(max_length=15, unique=True)
    merk = models.CharField(max_length=50)
    model_kendaraan = models.CharField(max_length=50)
    tahun = models.PositiveIntegerField()

    def get_tipe(self):
        return "Kendaraan"

    def deskripsi_khusus(self):
        return ""

    @property
    def ikon(self):
        """Nama ikon SVG (#i-<ikon>) untuk kendaraan ini. Ditimpa tiap subkelas."""
        return "mobil"

    @classmethod
    def relasi_subkelas(cls, awalan=""):
        """Nama relasi subkelas untuk select_related, mis. ("kendaraan__mobil", ...).

        awalan: jalur dari model lain ke Kendaraan, mis. "kendaraan__" dari
        TransaksiServis. Kosong kalau query-nya langsung atas Kendaraan.
        """
        return tuple(f"{awalan}{nama}" for nama in cls.SUBKELAS)

    @classmethod
    def model_subkelas(cls):
        """Class setiap subkelas (Mobil, Motor), dibaca dari SUBKELAS."""
        return tuple(getattr(cls, nama).related.related_model for nama in cls.SUBKELAS)

    def spesifik(self):
        """Objek subkelas yang sebenarnya (Mobil atau Motor), atau diri sendiri.

        Kendaraan yang diambil lewat relasi (transaksi.kendaraan) berupa objek
        induk, sehingga get_tipe() dan deskripsi_khusus() miliknya hanya versi
        umum. Method ini mengembalikan objek subkelasnya supaya perilaku
        polimorfisnya jalan. Kalau sudah subkelas, dikembalikan apa adanya.
        """
        if type(self) is not Kendaraan:
            return self
        for nama in self.SUBKELAS:
            try:
                return getattr(self, nama)
            except ObjectDoesNotExist:
                continue
        return self

    def __str__(self):
        return f"{self.merk} {self.model_kendaraan} - {self.no_polisi}"

    def alasan_tidak_bisa_dihapus(self):
        """None kalau kendaraan boleh dihapus, atau teks alasan kalau tidak.

        Kendaraan yang pernah diservis tidak boleh dihapus, apa pun status
        servisnya. Riwayat servis adalah catatan bengkel, bukan milik
        pelanggan semata: di dalamnya ada tagihan (yang belum dibayar pun),
        sparepart yang sudah mengurangi stok, dan angka di laporan.

        Dulu hanya servis yang sudah dibayar yang tertahan, jadi pelanggan
        bisa menghapus kendaraannya beserta tagihan yang belum dia bayar.

        transaksiservis_set adalah relasi balik bawaan dari
        servis.TransaksiServis.kendaraan (field itu tanpa related_name, dan
        nama bawaannya sudah dipakai halaman admin). Dipakai lewat relasi
        balik supaya app kendaraan tidak perlu mengimpor app servis, yang
        justru mengimpor kendaraan.
        """
        if self.transaksiservis_set.exists():
            return (
                "Kendaraan ini tidak bisa dihapus karena sudah punya riwayat "
                "servis di bengkel. Riwayatnya disimpan sebagai catatan bengkel."
            )
        # Pengajuan servis yang masih menunggu kasir. PengajuanServis.kendaraan
        # memakai CASCADE, jadi tanpa pemeriksaan ini pengajuannya hilang diam-diam
        # dari antrian kasir. Teks "MENUNGGU" = PengajuanServis.STATUS_MENUNGGU;
        # ditulis langsung karena app ini tidak boleh mengimpor app servis.
        if self.pengajuan_servis.filter(status="MENUNGGU").exists():
            return (
                "Kendaraan ini masih punya pengajuan servis yang menunggu "
                "persetujuan kasir. Batalkan pengajuannya dulu."
            )
        return None

    @property
    def bisa_dihapus(self):
        return self.alasan_tidak_bisa_dihapus() is None


class Mobil(Kendaraan):
    jumlah_pintu = models.PositiveIntegerField()
    jenis_mobil = models.CharField(max_length=30)  # contoh: SUV, Sedan, MPV

    def get_tipe(self):
        return "Mobil"

    def deskripsi_khusus(self):
        return f"{self.jenis_mobil}, {self.jumlah_pintu} pintu"

    @property
    def ikon(self):
        return "mobil"


class Motor(Kendaraan):
    jenis_motor = models.CharField(max_length=30)  # contoh: Matic, Bebek, Sport
    kapasitas_mesin = models.PositiveIntegerField(help_text="dalam cc")

    def get_tipe(self):
        return "Motor"

    def deskripsi_khusus(self):
        return f"{self.jenis_motor}, {self.kapasitas_mesin} cc"

    @property
    def ikon(self):
        return "motor"
