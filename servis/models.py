from django.db import models


class TransaksiServis(models.Model):
    STATUS_MENUNGGU = "MENUNGGU"
    STATUS_MENUNGGU_KONFIRMASI = "MENUNGGU_KONFIRMASI"
    STATUS_DIKERJAKAN = "DIKERJAKAN"
    STATUS_SELESAI = "SELESAI"
    STATUS_DIBATALKAN = "DIBATALKAN"
    STATUS_CHOICES = [
        (STATUS_MENUNGGU, "Menunggu"),
        (STATUS_MENUNGGU_KONFIRMASI, "Menunggu Konfirmasi"),
        (STATUS_DIKERJAKAN, "Dikerjakan"),
        (STATUS_SELESAI, "Selesai"),
        (STATUS_DIBATALKAN, "Dibatalkan"),
    ]

    kode_transaksi = models.CharField(max_length=50, unique=True, verbose_name="Kode Transaksi")
    tanggal = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_MENUNGGU)
    mekanik = models.ForeignKey(
        "accounts.Mekanik", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transaksi_servis", verbose_name="Mekanik",
    )
    total_biaya = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.kode_transaksi
