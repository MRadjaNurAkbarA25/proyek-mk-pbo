"""Model FR-35: Supplier dan Pembelian Sparepart.

Alur: DRAF (barang ditambah, stok belum berubah) -> selesaikan() (stok bertambah
sekaligus dalam satu transaksi database, status SELESAI).

Sesuai NFR-4:
    Abstraction    DetailPembelian memakai BarisTransaksi (abstract).
    Inheritance    DetailPembelian mewarisi BarisTransaksi.
    Encapsulation  Aturan draf/selesai hanya lewat method model, bukan view.
    Polymorphism   hitung_subtotal() sama, harga berbeda: beli vs jual.
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from pelanggan.templatetags.angka import rupiah
from sparepart.models import BarisTransaksi, Sparepart


class TanpaHapusMassalQuerySet(models.QuerySet):
    """QuerySet yang menolak `.delete()` massal, karena itu langsung ke SQL dan melewati aturan model.

    Hapus yang sah: `Supplier.nonaktifkan()`, `hapus_draf()`, `hapus_barang()`.
    """

    def delete(self):
        raise ValidationError(
            "Penghapusan massal tidak diizinkan. "
            "Gunakan method pada objeknya (nonaktifkan / hapus_draf / hapus_barang)."
        )


class Supplier(models.Model):
    """Pemasok barang. Tidak dihapus, hanya dinonaktifkan (FR-35)."""

    objects = TanpaHapusMassalQuerySet.as_manager()

    nama = models.CharField(max_length=100, verbose_name="Nama Supplier")
    telepon = models.CharField(max_length=30, blank=True, verbose_name="Telepon / WhatsApp")
    alamat = models.TextField(blank=True, verbose_name="Alamat")
    catatan = models.TextField(blank=True, verbose_name="Catatan")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Daftar Supplier"
        ordering = ["nama"]

    def __str__(self):
        return self.nama

    # ------------------------------------------- encapsulation: kelola status
    def nonaktifkan(self):
        if not self.aktif:
            raise ValidationError(f"Supplier '{self.nama}' sudah nonaktif.")
        self.aktif = False
        self.save(update_fields=["aktif"])

    def aktifkan(self):
        if self.aktif:
            raise ValidationError(f"Supplier '{self.nama}' sudah aktif.")
        self.aktif = True
        self.save(update_fields=["aktif"])

    def delete(self, *args, **kwargs):
        """Tolak penghapusan: supplier hanya boleh dinonaktifkan (FR-35) agar riwayat pembelian utuh."""
        raise ValidationError(
            f"Supplier '{self.nama}' tidak bisa dihapus, hanya dinonaktifkan."
        )


class PembelianSparepart(models.Model):
    """Satu transaksi pembelian barang dari supplier (FR-35)."""

    objects = TanpaHapusMassalQuerySet.as_manager()

    @classmethod
    def draf(cls):
        """Pembelian yang belum diselesaikan (stok belum bertambah)."""
        return cls.objects.filter(status=cls.STATUS_DRAF)

    METODE_TUNAI = "TUNAI"
    METODE_TRANSFER = "TRANSFER"
    METODE_CHOICES = [
        (METODE_TUNAI, "Tunai"),
        (METODE_TRANSFER, "Transfer"),
    ]

    STATUS_DRAF = "DRAF"
    STATUS_SELESAI = "SELESAI"
    STATUS_CHOICES = [
        (STATUS_DRAF, "Draf"),
        (STATUS_SELESAI, "Selesai"),
    ]

    kode = models.CharField(max_length=30, unique=True, editable=False, verbose_name="Kode Pembelian")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="pembelian", verbose_name="Supplier"
    )
    tanggal = models.DateField(default=timezone.localdate, verbose_name="Tanggal Pembelian")
    metode_bayar = models.CharField(max_length=20, choices=METODE_CHOICES, verbose_name="Metode Bayar")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAF, verbose_name="Status")
    dicatat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pembelian_dicatat",
        verbose_name="Dicatat Oleh",
    )
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Total")

    class Meta:
        verbose_name = "Pembelian Sparepart"
        verbose_name_plural = "Data Pembelian Sparepart"
        ordering = ["-tanggal", "-pk"]

    def __str__(self):
        return f"{self.kode} - {self.supplier.nama}"

    def clean(self):
        self._pastikan_supplier_aktif()

    def save(self, *args, **kwargs):
        self._pastikan_status_tidak_mundur()
        self._pastikan_supplier_aktif()
        # Kode dokumen dibuat dua tahap supaya memuat primary key: simpan dulu
        # dengan kode sementara, lalu tulis `PB-YYYYMMDD-001` permanen.
        if self.kode:
            return super().save(*args, **kwargs)

        # Model bisa dibuat dengan tanggal string ('2026-10-22') atau objek
        # date; normalisasi supaya format kode tidak gagal.
        tanggal = self.tanggal
        if isinstance(tanggal, str):
            tanggal = date.fromisoformat(tanggal)

        with transaction.atomic():
            self.kode = f"TMP-{uuid4().hex[:12]}"
            super().save(*args, **kwargs)
            self.kode = f"PB-{tanggal:%Y%m%d}-{self.pk:03d}"
            super().save(update_fields=["kode"])

    # ------------------------------------------------------ enkapsulasi aturan
    def _pastikan_draf(self, aksi):
        if self.status != self.STATUS_DRAF:
            raise ValidationError(f"Pembelian yang sudah selesai tidak bisa {aksi}.")

    def _pastikan_supplier_aktif(self):
        """Hanya supplier aktif yang bisa DIPILIH (FR-35); draf lama tetap boleh diselesaikan."""
        if self.supplier_id is None:
            return
        lama = None
        if not self._state.adding:
            lama = type(self).objects.filter(pk=self.pk).values_list("supplier_id", flat=True).first()
        if lama != self.supplier_id and not self.supplier.aktif:
            raise ValidationError({"supplier": f"Supplier '{self.supplier.nama}' nonaktif dan tidak bisa dipilih."})

    def _pastikan_status_tidak_mundur(self):
        """SELESAI tidak boleh kembali ke DRAF, supaya selesaikan() tidak menambah stok dua kali."""
        if not self.pk:
            return
        status_lama = (
            type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
        )
        if status_lama == self.STATUS_SELESAI and self.status != self.STATUS_SELESAI:
            raise ValidationError(
                "Pembelian yang sudah selesai tidak bisa dibuka kembali menjadi draf."
            )

    @transaction.atomic
    def tambah_barang(self, sparepart, jumlah, harga_beli):
        """Tambahkan satu barang ke draf. Stok belum berubah di sini."""
        self._pastikan_draf("diubah")
        # Jumlah & harga > 0 dijaga DetailPembelian.save().
        DetailPembelian.objects.create(
            pembelian=self, sparepart=sparepart, jumlah=jumlah, harga_satuan=harga_beli,
        )
        self.hitung_total()

    @transaction.atomic
    def hapus_barang(self, detail):
        """Hapus satu barang dari draf (stok belum berubah, jadi tidak perlu dibalik)."""
        self._pastikan_draf("diubah")
        if detail.pembelian_id != self.pk:
            raise ValidationError("Barang ini bukan bagian dari pembelian ini.")
        detail.delete()
        self.hitung_total()

    def hitung_total(self):
        """Jumlahkan seluruh subtotal (FR-35: total dihitung otomatis)."""
        total = self.detail.aggregate(total=Sum("subtotal"))["total"] or Decimal("0")
        self.total = total
        self.save(update_fields=["total"])
        return total

    @transaction.atomic
    def selesaikan(self):
        """Seluruh stok bertambah sekaligus dan status SELESAI.

        Draf kosong ditolak; select_for_update supaya aman bila dua proses bersamaan.
        """
        # Status di memori bisa basi (klik ganda): baca ulang supaya stok tidak bertambah dua kali.
        self.refresh_from_db(fields=["status"])
        self._pastikan_draf("diselesaikan")
        if not self.detail.exists():
            raise ValidationError("Pembelian tanpa barang tidak bisa diselesaikan.")

        for baris in self.detail.select_related("sparepart"):
            sp = Sparepart.objects.select_for_update().get(pk=baris.sparepart_id)
            sp.tambah_stok(baris.jumlah)

        self.hitung_total()
        self.status = self.STATUS_SELESAI
        self.save(update_fields=["status"])

    def delete(self, *args, **kwargs):
        """Tolak menghapus dokumen selesai: asal-usul stok harus tetap bisa ditelusuri."""
        self._pastikan_draf("dihapus")
        return super().delete(*args, **kwargs)

    def hapus_draf(self):
        """Hapus draf. Pembelian yang sudah selesai tidak bisa dihapus."""
        self.delete()


class DetailPembelian(BarisTransaksi):
    """Satu baris barang dalam pembelian. Mewarisi BarisTransaksi (inheritance)."""

    objects = TanpaHapusMassalQuerySet.as_manager()

    pembelian = models.ForeignKey(
        PembelianSparepart, on_delete=models.CASCADE, related_name="detail", verbose_name="Pembelian"
    )
    sparepart = models.ForeignKey(
        Sparepart, on_delete=models.PROTECT, related_name="detail_pembelian", verbose_name="Sparepart"
    )
    # Tulis ulang harga_satuan milik induk supaya labelnya sesuai konteks:
    # di sini harganya adalah harga BELI, bukan harga jual.
    harga_satuan = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Harga Beli Satuan")

    class Meta:
        verbose_name = "Detail Pembelian"
        verbose_name_plural = "Rincian Pembelian"

    def clean(self):
        self._pastikan_positif()

    def _pastikan_positif(self):
        # None = field kosong; sudah ditolak validasi field-nya sendiri.
        if self.jumlah is not None and self.jumlah <= 0:
            raise ValidationError({"jumlah": "Jumlah harus lebih dari 0."})
        if self.harga_satuan is not None and self.harga_satuan <= 0:
            raise ValidationError({"harga_satuan": "Harga beli harus lebih dari 0."})

    def save(self, *args, **kwargs):
        self._pastikan_positif()
        # Polymorphism: cara memanggil sama dengan DetailSparepart.save(),
        # tapi yang dihitung adalah subtotal harga beli.
        self.subtotal = self.hitung_subtotal()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Baris pada pembelian selesai tidak boleh hilang (total & stok jadi bohong)."""
        self.pembelian._pastikan_draf("diubah")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.sparepart.nama} ({self.jumlah} x {rupiah(self.harga_satuan)})"