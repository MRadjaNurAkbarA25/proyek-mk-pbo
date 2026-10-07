from django.db import models
from django.core.exceptions import ValidationError

class Sparepart(models.Model):
    kode = models.CharField(max_length=50, unique=True, verbose_name="Kode Sparepart")
    nama = models.CharField(max_length=100, verbose_name="Nama Sparepart")
    kategori = models.CharField(max_length=50, verbose_name="Kategori")
    harga = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Harga (Rp)")
    stok = models.IntegerField(default=0, verbose_name="Jumlah Stok")
    stok_minimum = models.IntegerField(default=5, verbose_name="Stok Minimum")

    class Meta:
        verbose_name = "Sparepart"
        verbose_name_plural = "Data Sparepart"
        ordering = ['nama']

    def __str__(self):
        return f"{self.kode} - {self.nama}"

    @property
    def is_stok_kritis(self):
        """Memeriksa apakah stok di bawah atau sama dengan stok minimum (FR-23)."""
        return self.stok <= self.stok_minimum

    def kurangi_stok(self, jumlah):
        """Metode OOP untuk pengurangan stok otomatis (FR-22)."""
        if jumlah <= 0:
            raise ValidationError("Jumlah pengurangan stok harus lebih dari 0.")
        if self.stok < jumlah:
            raise ValidationError(f"Stok {self.nama} tidak mencukupi (Tersedia: {self.stok}, Diminta: {jumlah}).")
        self.stok -= jumlah
        self.save()

    def tambah_stok(self, jumlah):
        """Metode OOP untuk penambahan stok."""
        if jumlah <= 0:
            raise ValidationError("Jumlah penambahan stok harus lebih dari 0.")
        self.stok += jumlah
        self.save()


class DetailSparepart(models.Model):
    transaksi = models.ForeignKey(
        'servis.TransaksiServis', 
        on_delete=models.CASCADE, 
        related_name='detail_sparepart',
        verbose_name="Transaksi Servis"
    )
    sparepart = models.ForeignKey(
        Sparepart, 
        on_delete=models.PROTECT, 
        related_name='detail_transaksi',
        verbose_name="Sparepart"
    )
    jumlah = models.PositiveIntegerField(default=1, verbose_name="Jumlah")
    harga_satuan = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Harga Satuan")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Subtotal")

    class Meta:
        verbose_name = "Detail Sparepart"
        verbose_name_plural = "Detail Sparepart Transaksi"

    def save(self, *args, **kwargs):
        # Menyalin harga dari master sparepart dan menghitung subtotal otomatis
        if not self.harga_satuan and self.sparepart:
            self.harga_satuan = self.sparepart.harga
        self.subtotal = self.jumlah * self.harga_satuan
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sparepart.nama} ({self.jumlah} x Rp {self.harga_satuan:,})"
