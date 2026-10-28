from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max, Q
from django.utils import timezone
from accounts.models import Pelanggan

# Status TransaksiServis.STATUS_SELESAI, ditulis langsung karena app ini tidak
# boleh mengimpor app servis (servis yang mengimpor kendaraan).
_SELESAI = "SELESAI"


class Kendaraan(models.Model):
    """Class induk: atribut yang dimiliki semua jenis kendaraan (Mobil, Motor)."""

    #: Nama relasi ke setiap subkelas. SATU-SATUNYA tempat daftar ini ditulis:
    #: query yang perlu memuat subkelas sekaligus memakai relasi_subkelas(),
    #: dan spesifik() mencoba nama-nama ini satu per satu. Menambah jenis
    #: kendaraan cukup menambah satu nama di sini plus satu class baru.
    SUBKELAS = ("mobil", "motor")

    #: Jarak antarservis berkala yang dianjurkan. Bawaan untuk semua
    #: kendaraan; tiap subkelas menimpanya dengan angkanya sendiri.
    INTERVAL_SERVIS_BERKALA_HARI = 90

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
        """Nama relasi subkelas untuk select_related; awalan mis. "kendaraan__" dari TransaksiServis."""
        return tuple(f"{awalan}{nama}" for nama in cls.SUBKELAS)

    @classmethod
    def model_subkelas(cls):
        """Class setiap subkelas (Mobil, Motor), dibaca dari SUBKELAS."""
        return tuple(getattr(cls, nama).related.related_model for nama in cls.SUBKELAS)

    def spesifik(self):
        """Objek subkelas sebenarnya (Mobil/Motor), supaya get_tipe() dan deskripsi_khusus() polimorfis.

        Kendaraan yang diambil lewat relasi berupa objek induk.
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

        Kendaraan yang pernah diservis (status apa pun) tidak boleh dihapus: riwayatnya
        berisi tagihan, pemakaian stok, dan angka laporan. Memakai relasi balik
        transaksiservis_set supaya app kendaraan tidak mengimpor app servis.
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

    # ---- Pengingat servis berkala ----
    @classmethod
    def dengan_servis_terakhir(cls, queryset):
        """Queryset + tanggal servis SELESAI terakhir, supaya halaman daftar
        tidak membuat satu query per kendaraan."""
        return queryset.annotate(selesai_terakhir=Max(
            "transaksiservis__tanggal", filter=Q(transaksiservis__status=_SELESAI)))

    def servis_terakhir(self):
        """Tanggal transaksi SELESAI terakhir kendaraan ini, atau None."""
        if "selesai_terakhir" in self.__dict__:
            waktu = self.selesai_terakhir
        else:
            waktu = self.transaksiservis_set.filter(status=_SELESAI).aggregate(t=Max("tanggal"))["t"]
        return timezone.localtime(waktu).date() if waktu else None

    def jatuh_tempo_servis(self):
        """servis_terakhir + interval jenis kendaraannya, atau None kalau belum pernah servis."""
        terakhir = self.servis_terakhir()
        if terakhir is None:
            return None
        # Objek induk (dari relasi) tetap memakai angka subkelasnya.
        return terakhir + timedelta(days=type(self.spesifik()).INTERVAL_SERVIS_BERKALA_HARI)

    @property
    def servis_berikutnya(self):
        """Jatuh tempo yang masih di depan, untuk ditampilkan; None kalau sudah lewat atau belum pernah servis."""
        jatuh_tempo = self.jatuh_tempo_servis()
        return jatuh_tempo if jatuh_tempo and jatuh_tempo > timezone.localdate() else None

    @property
    def perlu_servis_berkala(self):
        """Jatuh tempo sudah lewat dan kendaraan sedang bebas (tidak diservis,
        tidak punya pengajuan menunggu)."""
        jatuh_tempo = self.jatuh_tempo_servis()
        if jatuh_tempo is None or jatuh_tempo > timezone.localdate():
            return False
        # Diimpor di sini: servis mengimpor kendaraan saat dimuat.
        from servis.models import TransaksiServis
        return TransaksiServis.alasan_kendaraan_tidak_bisa_dilayani(self) is None


class Mobil(Kendaraan):
    INTERVAL_SERVIS_BERKALA_HARI = 180

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
    INTERVAL_SERVIS_BERKALA_HARI = 60

    jenis_motor = models.CharField(max_length=30)  # contoh: Matic, Bebek, Sport
    kapasitas_mesin = models.PositiveIntegerField(help_text="dalam cc")

    def get_tipe(self):
        return "Motor"

    def deskripsi_khusus(self):
        return f"{self.jenis_motor}, {self.kapasitas_mesin} cc"

    @property
    def ikon(self):
        return "motor"
