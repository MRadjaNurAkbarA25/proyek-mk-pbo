import uuid

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import Sum

from accounts.models import Mekanik, Pelanggan
from kendaraan.models import Kendaraan
from sparepart.models import DetailSparepart, Sparepart


class TransaksiServis(models.Model):
    """Transaksi servis. Alur status dijaga oleh method di class ini."""

    TIPE_DI_BENGKEL = "DI_BENGKEL"
    TIPE_HOME_SERVICE = "HOME_SERVICE"

    TIPE_CHOICES = [
        (TIPE_DI_BENGKEL, "Di Bengkel"),
        (TIPE_HOME_SERVICE, "Home Service"),
    ]

    STATUS_MENUNGGU = "MENUNGGU"
    STATUS_MENUNGGU_KONFIRMASI_MEKANIK = "MENUNGGU_KONFIRMASI_MEKANIK"
    STATUS_MENUNGGU_KONFIRMASI = "MENUNGGU_KONFIRMASI"
    STATUS_DIKERJAKAN = "DIKERJAKAN"
    STATUS_SELESAI = "SELESAI"
    STATUS_DIBATALKAN = "DIBATALKAN"

    STATUS_CHOICES = [
        (STATUS_MENUNGGU, "Menunggu"),
        (
            STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
            "Menunggu Konfirmasi Mekanik",
        ),
        (
            STATUS_MENUNGGU_KONFIRMASI,
            "Menunggu Konfirmasi Pelanggan",
        ),
        (STATUS_DIKERJAKAN, "Dikerjakan"),
        (STATUS_SELESAI, "Selesai"),
        (STATUS_DIBATALKAN, "Dibatalkan"),
    ]

    STATUS_AKTIF = [
        STATUS_MENUNGGU,
        STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
        STATUS_MENUNGGU_KONFIRMASI,
        STATUS_DIKERJAKAN,
    ]

    kode_transaksi = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Kode Transaksi",
    )

    pelanggan = models.ForeignKey(
        Pelanggan,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    kendaraan = models.ForeignKey(
        Kendaraan,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    mekanik = models.ForeignKey(
        Mekanik,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaksi_servis",
    )

    tanggal = models.DateTimeField(auto_now_add=True)

    keluhan = models.TextField(
    blank=True,
    default=""
)
    diagnosis = models.TextField(
        null=True,
        blank=True,
    )

    rekomendasi_perbaikan = models.TextField(
        null=True,
        blank=True,
    )

    konfirmasi_pelanggan = models.BooleanField(
        null=True,
        blank=True,
    )

    tipe_layanan = models.CharField(
        max_length=20,
        choices=TIPE_CHOICES,
        default=TIPE_DI_BENGKEL,
    )

    lokasi_servis = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_MENUNGGU,
    )

    total_biaya = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    def __str__(self):
        return self.kode_transaksi

    def save(self, *args, **kwargs):
        if self.kode_transaksi:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            self.kode_transaksi = f"TMP-{uuid.uuid4().hex[:12]}"

            super().save(*args, **kwargs)

            self.kode_transaksi = (
                f"TRX-{self.tanggal:%Y%m%d}-{self.pk:05d}"
            )

            super().save(
                update_fields=["kode_transaksi"]
            )

    # =========================================================
    # PROPERTI BANTU
    # =========================================================

    @property
    def kendaraan_spesifik(self):
        """
        Mengembalikan instance Mobil/Motor/Truk
        agar polymorphism dapat digunakan.
        """

        for nama in ("mobil", "motor", "truk"):
            try:
                return getattr(self.kendaraan, nama)
            except ObjectDoesNotExist:
                continue

        return self.kendaraan

    @property
    def bisa_didiagnosis(self):
        return self.status in (
            self.STATUS_MENUNGGU,
            self.STATUS_MENUNGGU_KONFIRMASI,
        )

    @property
    def bisa_diubah_itemnya(self):
        return self.status == self.STATUS_DIKERJAKAN

    @property
    def bisa_dilanjutkan_di_bengkel(self):
        return (
            self.tipe_layanan == self.TIPE_HOME_SERVICE
            and self.status in (
                self.STATUS_MENUNGGU,
                self.STATUS_MENUNGGU_KONFIRMASI,
                self.STATUS_DIKERJAKAN,
            )
        )

    # =========================================================
    # VALIDASI INTERNAL
    # =========================================================

    def _pastikan_status(self, *diizinkan, aksi):
        if self.status not in diizinkan:
            raise ValidationError(
                f"Tidak bisa {aksi} karena status transaksi "
                f"saat ini '{self.get_status_display()}'."
            )

    def _pastikan_home_service(self, aksi):
        if self.tipe_layanan != self.TIPE_HOME_SERVICE:
            raise ValidationError(
                f"Tidak bisa {aksi}: transaksi ini bukan home service."
            )

    def _pastikan_punya_mekanik(self):
        if not self.mekanik_id:
            raise ValidationError(
                "Transaksi ini belum memiliki mekanik."
            )

    def _sinkronkan_mekanik(self):
        if self.mekanik_id:
            self.mekanik.perbarui_status_otomatis()

    # =========================================================
    # PERHITUNGAN BIAYA
    # =========================================================

    def hitung_total(self):
        """
        Total =
        subtotal semua layanan +
        subtotal semua sparepart.
        """

        layanan = (
            self.detail_servis.aggregate(
                t=Sum("subtotal")
            )["t"]
            or 0
        )

        sparepart = (
            self.detail_sparepart.aggregate(
                t=Sum("subtotal")
            )["t"]
            or 0
        )

        self.total_biaya = layanan + sparepart

        self.save(
            update_fields=["total_biaya"]
        )

        return self.total_biaya

    # =========================================================
    # ALUR MEKANIK
    # =========================================================

    def ambil_oleh(self, mekanik):
        """
        Mekanik mengambil pekerjaan dari antrian bengkel.
        """

        if mekanik.status == Mekanik.STATUS_CUTI:
            raise ValidationError(
                "Anda sedang cuti dan tidak bisa mengambil pekerjaan."
            )

        diambil = type(self).objects.filter(
            pk=self.pk,
            mekanik__isnull=True,
            status=self.STATUS_MENUNGGU,
            tipe_layanan=self.TIPE_DI_BENGKEL,
        ).update(
            mekanik=mekanik
        )

        if not diambil:
            raise ValidationError(
                "Pekerjaan ini sudah diambil mekanik lain "
                "atau tidak tersedia lagi."
            )

        self.mekanik = mekanik

    @transaction.atomic
    def terima_home_service(self):
        """Mekanik menerima pekerjaan home service."""

        self._pastikan_home_service(
            "menerima home service"
        )

        self._pastikan_status(
            self.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
            aksi="menerima home service",
        )

        self._pastikan_punya_mekanik()

        self.mekanik.refresh_from_db(
            fields=["status"]
        )

        if not self.mekanik.bisa_menerima_pekerjaan:
            raise ValidationError(
                "Status Anda harus 'Tersedia' "
                "untuk menerima home service."
            )

        self.status = self.STATUS_MENUNGGU

        self.save(
            update_fields=["status"]
        )

        self._sinkronkan_mekanik()

    @transaction.atomic
    def tolak_home_service(self):
        """Mekanik menolak pekerjaan home service."""

        self._pastikan_home_service(
            "menolak home service"
        )

        self._pastikan_status(
            self.STATUS_MENUNGGU_KONFIRMASI_MEKANIK,
            aksi="menolak home service",
        )

        self.status = self.STATUS_DIBATALKAN

        self.save(
            update_fields=["status"]
        )

    def input_diagnosis(
        self,
        diagnosis,
        rekomendasi,
    ):
        """
        Mekanik memasukkan diagnosis dan
        rekomendasi perbaikan.
        """

        self._pastikan_status(
            self.STATUS_MENUNGGU,
            self.STATUS_MENUNGGU_KONFIRMASI,
            aksi="mengisi diagnosis",
        )

        self._pastikan_punya_mekanik()

        if not (diagnosis or "").strip():
            raise ValidationError(
                "Diagnosis wajib diisi."
            )

        if not (rekomendasi or "").strip():
            raise ValidationError(
                "Rekomendasi perbaikan wajib diisi."
            )

        self.diagnosis = diagnosis.strip()

        self.rekomendasi_perbaikan = (
            rekomendasi.strip()
        )

        self.konfirmasi_pelanggan = None

        self.status = (
            self.STATUS_MENUNGGU_KONFIRMASI
        )

        self.save(
            update_fields=[
                "diagnosis",
                "rekomendasi_perbaikan",
                "konfirmasi_pelanggan",
                "status",
            ]
        )

    @transaction.atomic
    def konfirmasi(self, setuju):
        """
        Pelanggan menyetujui atau menolak
        diagnosis mekanik.
        """

        self._pastikan_status(
            self.STATUS_MENUNGGU_KONFIRMASI,
            aksi="mengonfirmasi diagnosis",
        )

        self.konfirmasi_pelanggan = bool(setuju)

        self.status = (
            self.STATUS_DIKERJAKAN
            if setuju
            else self.STATUS_DIBATALKAN
        )

        self.save(
            update_fields=[
                "konfirmasi_pelanggan",
                "status",
            ]
        )

        self._sinkronkan_mekanik()

    @transaction.atomic
    def tambah_layanan(
        self,
        jenis_servis,
        jumlah=1,
    ):
        """
        Menambahkan jenis layanan ke transaksi.
        """

        self._pastikan_status(
            self.STATUS_DIKERJAKAN,
            aksi="menambah layanan",
        )

        if jumlah < 1:
            raise ValidationError(
                "Jumlah minimal 1."
            )

        detail = DetailServis.objects.create(
            transaksi=self,
            jenis_servis=jenis_servis,
            jumlah=jumlah,
        )

        self.hitung_total()

        return detail

    @transaction.atomic
    def tambah_sparepart(self, sparepart, jumlah=1):
        """Menambahkan sparepart ke transaksi dan mengurangi stok otomatis."""
        self._pastikan_status(self.STATUS_DIKERJAKAN, aksi="mencatat sparepart")

        # Kunci baris sparepart agar stok aman jika dua mekanik mencatat bersamaan
        sp = Sparepart.objects.select_for_update().get(pk=sparepart.pk)
        sp.kurangi_stok(jumlah)  # FR-22; ValidationError jika stok kurang / jumlah <= 0

        detail = DetailSparepart.objects.create(
            transaksi=self,
            sparepart=sp,
            jumlah=jumlah,
            harga_satuan=sp.harga,
        )

        self.hitung_total()
        return detail

    @transaction.atomic
    def selesaikan(self):
        """
        Menyelesaikan transaksi servis.
        """

        self._pastikan_status(
            self.STATUS_DIKERJAKAN,
            aksi="menyelesaikan servis",
        )

        self.hitung_total()

        self.status = self.STATUS_SELESAI

        self.save(
            update_fields=["status"]
        )

        self._sinkronkan_mekanik()

    @transaction.atomic
    def lanjutkan_di_bengkel(self):
        """
        Home service yang belum selesai
        dilanjutkan di bengkel.
        """

        self._pastikan_home_service(
            "dilanjutkan di bengkel"
        )

        self._pastikan_status(
            self.STATUS_MENUNGGU,
            self.STATUS_MENUNGGU_KONFIRMASI,
            self.STATUS_DIKERJAKAN,
            aksi="melanjutkan di bengkel",
        )

        self.tipe_layanan = self.TIPE_DI_BENGKEL
        self.lokasi_servis = None

        self.save(
            update_fields=[
                "tipe_layanan",
                "lokasi_servis",
            ]
        )

        self._sinkronkan_mekanik()


class DetailServis(models.Model):
    """
    Composition:
    satu baris layanan dalam transaksi.
    """

    transaksi = models.ForeignKey(
        TransaksiServis,
        on_delete=models.CASCADE,
        related_name="detail_servis",
    )

    # JenisServis sekarang berada di aplikasi mekanik.
    jenis_servis = models.ForeignKey(
        "mekanik.JenisServis",
        on_delete=models.PROTECT,
        related_name="detail_transaksi",
    )

    jumlah = models.PositiveIntegerField(
        default=1
    )

    harga = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    def save(self, *args, **kwargs):
        if not self.harga:
            self.harga = self.jenis_servis.harga

        self.subtotal = self.jumlah * self.harga

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.jenis_servis.nama_servis} "
            f"x{self.jumlah}"
        )