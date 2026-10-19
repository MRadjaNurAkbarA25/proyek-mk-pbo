from django.db import models
from accounts.models import Pelanggan


class Kendaraan(models.Model):
    """Class induk: atribut yang dimiliki semua jenis kendaraan."""
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


class Motor(Kendaraan):
    jenis_motor = models.CharField(max_length=30)  # contoh: Matic, Bebek, Sport
    kapasitas_mesin = models.PositiveIntegerField(help_text="dalam cc")

    def get_tipe(self):
        return "Motor"

    def deskripsi_khusus(self):
        return f"{self.jenis_motor}, {self.kapasitas_mesin} cc"


class Truk(Kendaraan):
    kapasitas_muatan_kg = models.PositiveIntegerField()
    jumlah_sumbu = models.PositiveIntegerField(default=2)

    def get_tipe(self):
        return "Truk"

    def deskripsi_khusus(self):
        return f"Muatan {self.kapasitas_muatan_kg} kg, {self.jumlah_sumbu} sumbu"