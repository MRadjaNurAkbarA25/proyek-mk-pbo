import uuid
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

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

    # FR-31 C. Berapa hari penuh pelanggan diberi waktu membawa kendaraannya
    # sebelum transaksinya dibatalkan sendiri. Dihitung per HARI, bukan per
    # jam: pelanggan yang mengajukan jam 23.00 tidak kehilangan satu hari
    # jatah hanya karena harinya hampir berganti.
    BATAS_HARI_KEDATANGAN = 3

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

    # FR-31. Transaksi yang dibuat kasir di meja selalu True: kendaraannya
    # memang sudah di depan mata. Transaksi hasil pengajuan pelanggan lahir
    # False, karena disetujui saat kendaraannya masih di rumah pemiliknya.
    # Antrian mekanik hanya menampilkan yang True, supaya mekanik tidak
    # mengambil pekerjaan untuk kendaraan yang belum ada di bengkel.
    kendaraan_hadir = models.BooleanField(
        default=True,
        verbose_name="Kendaraan sudah tiba di bengkel",
    )

    # Rencana tanggal pelanggan membawa kendaraannya. Disalin dari pengajuan
    # saat kasir menerima, dan boleh diubah pelanggan selama belum tiba.
    tanggal_rencana_datang = models.DateField(
        null=True,
        blank=True,
        verbose_name="Rencana tiba di bengkel",
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
    def menunggu_kedatangan(self):
        """Sudah disetujui tapi kendaraannya belum sampai di bengkel (FR-31).

        Tiga syarat, semuanya perlu:

        1. Pekerjaannya memang dikerjakan DI BENGKEL. Pada home service
           kendaraan tidak pernah datang ke bengkel dan memang tidak perlu,
           jadi pertanyaan "sudah tiba atau belum" tidak berlaku di sana.
        2. Kendaraannya belum ditandai tiba.
        3. Transaksinya masih berjalan; kalau sudah selesai atau dibatalkan,
           pertanyaannya tidak ada artinya.
        """
        return (
            self.tipe_layanan == self.TIPE_DI_BENGKEL
            and not self.kendaraan_hadir
            and self.status in self.STATUS_AKTIF
        )

    @property
    def tanggal_masih_bisa_diubah(self):
        """Tanggal rencana hanya berguna selama kendaraannya belum tiba."""
        return self.menunggu_kedatangan

    def batas_kedatangan(self):
        """Tanggal terakhir kendaraan boleh tiba sebelum transaksinya batal sendiri.

        SATU-SATUNYA tempat rumus ini ditulis. Penyapu otomatis maupun
        tampilan halaman sama-sama memanggil method ini, supaya keduanya
        tidak pernah menghitung batas yang berbeda.

        Patokannya tanggal yang LEBIH BELAKANGAN antara:
          - tanggal transaksi ini dibuat (= saat kasir menerima pengajuan,
            atau saat mekanik mengalihkan home service ke bengkel), dan
          - tanggal rencana datang yang diisi pelanggan.

        Kalau hanya dihitung dari rencana datang, transaksi yang baru
        disetujui seminggu setelah tanggal rencananya akan lahir dalam
        keadaan sudah lewat batas dan langsung dibatalkan beberapa detik
        setelah disetujui. Memakai yang lebih belakangan menjamin
        pelanggan selalu dapat jatah hari penuh sejak transaksinya ada.

        Mengembalikan None kalau transaksinya memang tidak sedang
        menunggu kedatangan.
        """
        if not self.menunggu_kedatangan:
            return None

        # localtime(), bukan .date() mentah: TIME_ZONE proyek ini
        # Asia/Makassar, dan tanggal UTC meleset delapan jam.
        mulai = timezone.localtime(self.tanggal).date()
        if self.tanggal_rencana_datang and self.tanggal_rencana_datang > mulai:
            mulai = self.tanggal_rencana_datang
        return mulai + timedelta(days=self.BATAS_HARI_KEDATANGAN)

    @property
    def kedatangan_lewat_batas(self):
        """Batasnya sudah terlampaui dan kendaraannya masih belum datang."""
        batas = self.batas_kedatangan()
        return batas is not None and timezone.localdate() > batas

    @transaction.atomic
    def batalkan_karena_tidak_datang(self):
        """Batalkan transaksi yang kendaraannya tidak kunjung tiba (FR-31 C).

        Pelanggan tidak bisa menghidupkannya lagi; kalau masih mau servis,
        dia membuat pengajuan baru. Itu memang disengaja: pengajuan yang
        bisa dibangkitkan berkali-kali membuat antrian kasir tidak pernah
        benar-benar bersih.
        """
        if not self.kedatangan_lewat_batas:
            raise ValidationError(
                "Transaksi ini belum melewati batas kedatangan."
            )

        self.status = self.STATUS_DIBATALKAN
        self.save(update_fields=["status"])
        self._sinkronkan_mekanik()

    @classmethod
    def alasan_kendaraan_tidak_bisa_dilayani(cls, kendaraan, abaikan_pengajuan=None):
        """None kalau kendaraan bebas dipesan, atau teks alasan kalau tidak.

        SATU-SATUNYA tempat aturan "satu kendaraan, satu pekerjaan berjalan"
        ditulis. Dipakai bertiga: form Ajukan Servis, form Home Service, dan
        pemeriksaan ulang saat kasir menerima pengajuan.

        Dulu aturan ini hanya dijaga di sisi Ajukan Servis. Home Service tidak
        memeriksa apa pun, jadi kendaraan yang sedang diservis masih bisa
        dipesankan home service, berkali-kali pula. Penjagaan satu sisi seperti
        itu memang mudah terjadi kalau aturannya ditulis di dalam class
        PengajuanServis: Home Service tidak punya alasan memanggilnya.

        abaikan_pengajuan: lewati satu pengajuan tertentu. Diperlukan saat
        kasir menerima, karena pengajuan yang sedang diproses memang
        berstatus MENUNGGU dan tidak boleh menghalangi dirinya sendiri.
        """
        if cls.objects.filter(
            kendaraan=kendaraan, status__in=cls.STATUS_AKTIF
        ).exists():
            return "Kendaraan ini masih dalam proses servis yang belum selesai."

        menunggu = PengajuanServis.objects.filter(
            kendaraan=kendaraan, status=PengajuanServis.STATUS_MENUNGGU
        )
        if abaikan_pengajuan is not None and abaikan_pengajuan.pk:
            menunggu = menunggu.exclude(pk=abaikan_pengajuan.pk)
        if menunggu.exists():
            return "Kendaraan ini masih punya pengajuan yang menunggu persetujuan kasir."

        return None

    @classmethod
    def sapu_kedatangan_lewat(cls):
        """Batalkan semua transaksi yang kendaraannya lewat batas. Kembalikan jumlahnya.

        Dipanggil dari halaman yang memang melihat data ini — daftar
        transaksi dan pengajuan kasir, serta halaman pengajuan dan riwayat
        pelanggan — jadi proyek ini tidak perlu cron atau scheduler
        tambahan untuk berjalan benar. Pemanggilan dari sisi pelanggan
        penting: tanpa itu, pelanggan bisa melihat transaksi yang
        seharusnya sudah batal hanya karena kasirnya belum membuka halaman.
        """
        calon = cls.objects.filter(
            tipe_layanan=cls.TIPE_DI_BENGKEL,
            kendaraan_hadir=False,
            status__in=cls.STATUS_AKTIF,
        )
        jumlah = 0
        for transaksi in calon:
            if transaksi.kedatangan_lewat_batas:
                transaksi.batalkan_karena_tidak_datang()
                jumlah += 1
        return jumlah

    @transaction.atomic
    def tandai_kendaraan_tiba(self):
        """Kasir menandai kendaraan sudah sampai; transaksi masuk antrian mekanik."""
        if self.kendaraan_hadir:
            raise ValidationError("Kendaraan ini sudah ditandai tiba sebelumnya.")
        if self.status not in self.STATUS_AKTIF:
            raise ValidationError(
                f"Tidak bisa menandai kedatangan: status transaksi "
                f"'{self.get_status_display()}'."
            )

        self.kendaraan_hadir = True
        self.save(update_fields=["kendaraan_hadir"])

    def ubah_rencana_datang(self, tanggal):
        """Pelanggan mengubah rencana tanggal membawa kendaraannya."""
        if not self.tanggal_masih_bisa_diubah:
            raise ValidationError(
                "Tanggal tidak bisa diubah lagi karena kendaraan sudah tiba "
                "atau transaksinya sudah tidak berjalan."
            )
        if tanggal and tanggal < timezone.localdate():
            raise ValidationError("Tanggal rencana datang tidak boleh di masa lalu.")

        self.tanggal_rencana_datang = tanggal
        self.save(update_fields=["tanggal_rencana_datang"])

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

        # kendaraan_hadir ikut disaring di sini, bukan hanya di query antrian,
        # supaya tidak bisa ditembus dengan POST langsung ke /mekanik/ambil/<pk>/
        # untuk kendaraan yang belum tiba di bengkel.
        diambil = type(self).objects.filter(
            pk=self.pk,
            mekanik__isnull=True,
            status=self.STATUS_MENUNGGU,
            tipe_layanan=self.TIPE_DI_BENGKEL,
            kendaraan_hadir=True,
        ).update(
            mekanik=mekanik
        )

        if not diambil:
            raise ValidationError(
                "Pekerjaan ini sudah diambil mekanik lain, "
                "kendaraannya belum tiba di bengkel, "
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
    def lanjutkan_di_bengkel(self, tanggal_rencana_datang):
        """
        Home service yang belum selesai
        dilanjutkan di bengkel.

        Tanggalnya WAJIB. Saat method ini dipanggil mekanik sedang berada di
        lokasi pelanggan dan kendaraannya masih di sana, jadi harus ada
        kesepakatan kapan kendaraan itu dibawa ke bengkel. Dulu tanggal ini
        tidak diminta dan kendaraan_hadir dibiarkan apa adanya, sehingga
        sistem mencatat kendaraan sudah di bengkel padahal masih di rumah
        pelanggan: tidak ada yang diberi tahu untuk membawanya, dan tombol
        "tandai tiba" milik kasir tidak berlaku.
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

        if not tanggal_rencana_datang:
            raise ValidationError(
                "Isi dulu tanggal kendaraan akan dibawa ke bengkel."
            )
        if tanggal_rencana_datang < timezone.localdate():
            raise ValidationError(
                "Tanggal kendaraan dibawa ke bengkel tidak boleh di masa lalu."
            )

        self.tipe_layanan = self.TIPE_DI_BENGKEL
        self.lokasi_servis = None
        self.kendaraan_hadir = False
        self.tanggal_rencana_datang = tanggal_rencana_datang

        self.save(
            update_fields=[
                "tipe_layanan",
                "lokasi_servis",
                "kendaraan_hadir",
                "tanggal_rencana_datang",
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


class PengajuanServis(models.Model):
    """FR-31: pelanggan mengajukan servis di bengkel, kasir yang menyetujui.

    Dibuat sebagai model terpisah, bukan status baru di TransaksiServis, karena:

    1. TransaksiServis membangkitkan kode resmi TRX-YYYYMMDD-00001 yang dipakai
       di nota pembayaran. Pengajuan yang akhirnya ditolak tidak boleh ikut
       memakan nomor itu.
    2. Alur status TransaksiServis (MENUNGGU -> ... -> SELESAI) sudah dijaga
       ketat oleh method-methodnya. Menambah status "belum disetujui" akan
       membuat semua pemeriksaan status itu harus ditulis ulang.

    Transaksi servis baru dibuat pada saat kasir menekan Terima, lewat alur
    `objects.create` yang sama dengan yang dipakai kasir saat membuat transaksi
    manual, sehingga pengajuan yang diterima langsung masuk antrian bengkel.
    """

    STATUS_MENUNGGU = "MENUNGGU"
    STATUS_DITERIMA = "DITERIMA"
    STATUS_DITOLAK = "DITOLAK"
    STATUS_DIBATALKAN = "DIBATALKAN"

    STATUS_CHOICES = [
        (STATUS_MENUNGGU, "Menunggu Persetujuan Kasir"),
        (STATUS_DITERIMA, "Diterima"),
        (STATUS_DITOLAK, "Ditolak"),
        (STATUS_DIBATALKAN, "Dibatalkan Pelanggan"),
    ]

    # Status yang sudah final; tidak bisa diproses atau dibatalkan lagi.
    STATUS_SELESAI_DIPROSES = [STATUS_DITERIMA, STATUS_DITOLAK, STATUS_DIBATALKAN]

    pelanggan = models.ForeignKey(
        Pelanggan, on_delete=models.CASCADE, related_name="pengajuan_servis"
    )
    kendaraan = models.ForeignKey(
        Kendaraan, on_delete=models.CASCADE, related_name="pengajuan_servis"
    )
    keluhan = models.TextField(verbose_name="Keluhan kendaraan")
    tanggal_rencana_datang = models.DateField(
        null=True,
        blank=True,
        verbose_name="Rencana datang ke bengkel",
        help_text="Boleh dikosongkan kalau belum pasti.",
    )
    tanggal_diajukan = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_MENUNGGU
    )
    catatan_kasir = models.TextField(
        blank=True,
        default="",
        verbose_name="Catatan / alasan dari kasir",
    )
    diproses_oleh = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan_servis_diproses",
    )
    diproses_pada = models.DateTimeField(null=True, blank=True)

    # Terisi hanya kalau pengajuan diterima; jadi jejak dari pengajuan ke
    # transaksi yang dihasilkannya.
    transaksi = models.OneToOneField(
        TransaksiServis,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan",
    )

    class Meta:
        ordering = ["-tanggal_diajukan"]
        verbose_name = "Pengajuan Servis"
        verbose_name_plural = "Pengajuan Servis"

    def __str__(self):
        return f"Pengajuan {self.kendaraan.no_polisi} ({self.get_status_display()})"

    # =========================================================
    # PROPERTI BANTU
    # =========================================================

    @property
    def masih_menunggu(self):
        return self.status == self.STATUS_MENUNGGU

    @property
    def kendaraan_spesifik(self):
        """Mobil/Motor/Truk, supaya get_tipe() dan deskripsi_khusus() polimorfis."""
        for nama in ("mobil", "motor", "truk"):
            try:
                return getattr(self.kendaraan, nama)
            except ObjectDoesNotExist:
                continue
        return self.kendaraan

    # =========================================================
    # ATURAN PENGAJUAN
    # =========================================================

    @classmethod
    def alasan_kendaraan_tidak_bisa(cls, kendaraan):
        """None kalau kendaraan boleh diajukan, atau teks alasan kalau tidak.

        Dipakai form (sebelum simpan) dan view (pemeriksaan ulang di server),
        supaya aturannya hanya ditulis satu kali.
        """
        return TransaksiServis.alasan_kendaraan_tidak_bisa_dilayani(kendaraan)

    def _pastikan_masih_menunggu(self, aksi):
        if not self.masih_menunggu:
            raise ValidationError(
                f"Tidak bisa {aksi}: pengajuan ini sudah "
                f"{self.get_status_display().lower()}."
            )

    # =========================================================
    # ALUR KASIR
    # =========================================================

    @transaction.atomic
    def terima(self, petugas):
        """Kasir menyetujui: buat transaksi servis dan masukkan ke antrian bengkel."""
        self._pastikan_masih_menunggu("menerima pengajuan")

        alasan = self.alasan_kendaraan_tidak_bisa_selain_ini()
        if alasan:
            raise ValidationError(alasan)

        transaksi_baru = TransaksiServis.objects.create(
            pelanggan=self.pelanggan,
            kendaraan=self.kendaraan,
            keluhan=self.keluhan,
            tipe_layanan=TransaksiServis.TIPE_DI_BENGKEL,
            # Kendaraan belum tentu sudah dibawa ke bengkel saat kasir
            # menyetujui, jadi transaksinya belum boleh masuk antrian mekanik
            # sampai kasir menandai kedatangannya.
            kendaraan_hadir=False,
            # Tanggal yang diminta pelanggan disalin ke transaksi. Mulai saat
            # ini yang berlaku adalah salinan di transaksi; pengajuan tetap
            # menyimpan tanggal yang diajukan semula sebagai catatan.
            tanggal_rencana_datang=self.tanggal_rencana_datang,
            # status default MENUNGGU, kode dibuat oleh TransaksiServis.save()
        )

        self.transaksi = transaksi_baru
        self.status = self.STATUS_DITERIMA
        self.diproses_oleh = petugas
        self.diproses_pada = timezone.now()
        self.save(
            update_fields=["transaksi", "status", "diproses_oleh", "diproses_pada"]
        )
        return transaksi_baru

    def alasan_kendaraan_tidak_bisa_selain_ini(self):
        """Seperti alasan_kendaraan_tidak_bisa, tapi mengabaikan pengajuan ini sendiri.

        Diperlukan saat kasir menerima: pengajuan yang sedang diproses memang
        berstatus MENUNGGU, jadi tidak boleh dianggap sebagai penghalang.
        """
        return TransaksiServis.alasan_kendaraan_tidak_bisa_dilayani(
            self.kendaraan, abaikan_pengajuan=self
        )

    @transaction.atomic
    def tolak(self, petugas, alasan):
        """Kasir menolak pengajuan. Alasan wajib supaya pelanggan tahu sebabnya."""
        self._pastikan_masih_menunggu("menolak pengajuan")

        if not (alasan or "").strip():
            raise ValidationError("Alasan penolakan wajib diisi.")

        self.status = self.STATUS_DITOLAK
        self.catatan_kasir = alasan.strip()
        self.diproses_oleh = petugas
        self.diproses_pada = timezone.now()
        self.save(
            update_fields=["status", "catatan_kasir", "diproses_oleh", "diproses_pada"]
        )

    # =========================================================
    # ALUR PELANGGAN
    # =========================================================

    def ubah_rencana_datang(self, tanggal):
        """Pelanggan mengubah tanggal pada pengajuan yang belum ditinjau kasir.

        Setelah pengajuan diterima, yang diubah bukan ini lagi melainkan
        TransaksiServis.ubah_rencana_datang(), supaya catatan pengajuan tetap
        menyimpan apa yang diminta semula.
        """
        self._pastikan_masih_menunggu("mengubah tanggal kedatangan")

        if tanggal and tanggal < timezone.localdate():
            raise ValidationError("Tanggal rencana datang tidak boleh di masa lalu.")

        self.tanggal_rencana_datang = tanggal
        self.save(update_fields=["tanggal_rencana_datang"])

    @transaction.atomic
    def batalkan(self):
        """Pelanggan menarik kembali pengajuan yang belum diproses kasir."""
        self._pastikan_masih_menunggu("membatalkan pengajuan")

        self.status = self.STATUS_DIBATALKAN
        self.diproses_pada = timezone.now()
        self.save(update_fields=["status", "diproses_pada"])