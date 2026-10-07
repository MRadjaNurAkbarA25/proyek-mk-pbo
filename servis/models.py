from django.db import models

class TransaksiServis(models.Model):
    kode_transaksi = models.CharField(max_length=50, unique=True, verbose_name="Kode Transaksi")
    tanggal = models.DateTimeField(auto_now_add=True)
    total_biaya = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.kode_transaksi