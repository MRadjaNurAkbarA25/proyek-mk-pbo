from django.db import models

class JenisServis(models.Model):
    nama_servis = models.CharField(max_length=100)
    deskripsi = models.TextField(blank=True)
    estimasi_waktu = models.PositiveIntegerField(
        help_text="Estimasi waktu dalam menit"
    )
    harga = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.nama_servis} (Rp {self.harga:,.0f})"