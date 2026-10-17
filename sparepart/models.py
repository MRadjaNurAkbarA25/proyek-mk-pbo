from django.db import models
from django.core.exceptions import ValidationError

class Sparepart(models.Model):
    # Tiga tingkat kondisi stok. Dipakai bersama oleh daftar sparepart,
    # peringatan stok, laporan stok admin, dan halaman admin Django, supaya
    # aturannya hanya ditulis sekali di sini.
    STOK_KOSONG = "KOSONG"
    STOK_MINIM = "MINIM"
    STOK_AMAN = "AMAN"

    LABEL_STOK = {
        STOK_KOSONG: "Stok Kosong",
        STOK_MINIM: "Stok Minim",
        STOK_AMAN: "Aman",
    }

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
    def status_stok(self):
        """Kondisi stok dalam tiga tingkat (FR-23).

        KOSONG : stok habis, sparepart ini sama sekali tidak bisa dipakai servis
        MINIM  : masih ada, tapi sudah menyentuh atau di bawah batas minimum
        AMAN   : di atas batas minimum

        Dibedakan menjadi tiga karena stok 0 dan stok 1 berbeda jauh artinya
        bagi mekanik: yang satu pekerjaan berhenti, yang satu masih jalan tapi
        harus segera dipesan.
        """
        if self.stok <= 0:
            return self.STOK_KOSONG
        if self.stok <= self.stok_minimum:
            return self.STOK_MINIM
        return self.STOK_AMAN

    @property
    def label_stok(self):
        """Teks status stok untuk ditampilkan, mis. 'Stok Minim'."""
        return self.LABEL_STOK[self.status_stok]

    @property
    def stok_habis(self):
        return self.status_stok == self.STOK_KOSONG

    @property
    def is_stok_kritis(self):
        """Perlu dipesan ulang: stok kosong ATAU sudah di batas minimum (FR-23).

        Tetap dipertahankan karena dipakai mekanik/views.py, laporan stok, dan
        kartu dashboard admin. Sekarang mengacu pada status_stok supaya tidak
        ada dua aturan terpisah yang bisa berbeda sendiri.
        """
        return self.status_stok in (self.STOK_KOSONG, self.STOK_MINIM)

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
