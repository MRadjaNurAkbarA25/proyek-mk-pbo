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