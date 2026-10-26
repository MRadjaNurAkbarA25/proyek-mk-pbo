from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from pelanggan.templatetags.angka import rupiah
from servis.models import TransaksiServis


class Pembayaran(models.Model):
    METODE_CASH = "CASH"
    METODE_TRANSFER = "TRANSFER"
    METODE_EWALLET = "E_WALLET"
    METODE_CHOICES = [
        (METODE_CASH, "Cash"),
        (METODE_TRANSFER, "Transfer"),
        (METODE_EWALLET, "E-Wallet / QRIS"),
    ]

    transaksi = models.OneToOneField(
        TransaksiServis, on_delete=models.PROTECT, related_name="pembayaran"
    )
    tanggal = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    metode = models.CharField(max_length=20, choices=METODE_CHOICES)
    # Cash: kasir/mekanik yang menerima uangnya. Non-tunai: kasir/admin yang
    # menyetujui buktinya. Kosong untuk pembayaran lama sebelum kolom ini ada.
    dicatat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pembayaran_dicatat",
    )

    def __str__(self):
        return f"Pembayaran {self.transaksi.kode_transaksi}"

    @staticmethod
    def pencatat_cash_sah(transaksi, user):
        """Servis di bengkel dicatat kasir; home service dicatat mekanik yang menanganinya.

        Home service yang dialihkan ke bengkel sudah berganti tipe menjadi
        DI_BENGKEL (TransaksiServis.lanjutkan_di_bengkel), jadi ikut kasir.
        """
        if transaksi.tipe_layanan == TransaksiServis.TIPE_HOME_SERVICE:
            return bool(transaksi.mekanik_id) and transaksi.mekanik.user_id == user.pk
        return user.role == "KASIR"

    @classmethod
    def catat_cash(cls, transaksi, uang_dibayar, oleh):
        if not cls.pencatat_cash_sah(transaksi, oleh):
            if transaksi.tipe_layanan == TransaksiServis.TIPE_HOME_SERVICE:
                raise ValidationError("Cash home service dicatat oleh mekanik yang menanganinya.")
            raise ValidationError("Cash servis di bengkel dicatat oleh kasir.")
        if BuktiPembayaran.menunggu_untuk(transaksi):
            raise ValidationError(
                "Pelanggan sudah mengirim bukti pembayaran non-tunai yang menunggu verifikasi."
            )
        return cls.buat(transaksi, cls.METODE_CASH, uang_dibayar=uang_dibayar, oleh=oleh)

    @classmethod
    def buat(cls, transaksi, metode, oleh=None, **data):
        if transaksi.status != TransaksiServis.STATUS_SELESAI:
            raise ValidationError("Hanya transaksi berstatus Selesai yang dapat dibayar.")
        if metode not in dict(cls.METODE_CHOICES):
            raise ValidationError("Metode pembayaran tidak valid.")
        existing = cls.objects.filter(transaksi=transaksi)
        if existing.exists():
            return existing.get()._resolve_retry(metode, data)
        try:
            with transaction.atomic():
                pembayaran = cls.objects.create(
                    transaksi=transaksi, total=transaksi.total_biaya, metode=metode,
                    dicatat_oleh=oleh,
                )
                if metode == cls.METODE_CASH:
                    PembayaranCash.objects.create(
                        pembayaran=pembayaran, uang_dibayar=data.get("uang_dibayar")
                    )
                elif metode == cls.METODE_TRANSFER:
                    PembayaranTransfer.objects.create(
                        pembayaran=pembayaran, nomor_referensi=data.get("nomor_referensi", "").strip()
                    )
                else:
                    PembayaranEWallet.objects.create(
                        pembayaran=pembayaran,
                        provider=data.get("provider", "").strip(),
                        nomor_transaksi=data.get("nomor_transaksi", "").strip(),
                    )
                return pembayaran
        except IntegrityError:
            winner = cls.objects.filter(transaksi=transaksi).first()
            if winner is None:
                raise  
            return winner._resolve_retry(metode, data)

    def _resolve_retry(self, metode, data):
        conflict = "Transaksi sudah dibayar dengan data pembayaran berbeda."
        if self.metode != metode:
            raise ValidationError(conflict, code="payment_conflict")
        fields = {
            self.METODE_CASH: ("uang_dibayar",),
            self.METODE_TRANSFER: ("nomor_referensi",),
            self.METODE_EWALLET: ("provider", "nomor_transaksi"),
        }[metode]
        detail = self.detail()
        if detail is None:
            raise ValidationError("Detail pembayaran yang tersimpan tidak ditemukan.")
        for name in fields:
            value = data.get(name)
            if isinstance(value, str):
                value = value.strip()
            value = detail._meta.get_field(name).clean(value, detail)
            if getattr(detail, name) != value:
                raise ValidationError(conflict, code="payment_conflict")
        return self

    def detail(self):
        for nama in ("pembayarancash", "pembayarantransfer", "pembayarane_wallet"):
            try:
                return getattr(self, nama)
            except (AttributeError, ObjectDoesNotExist):
                continue
        return None

    def ringkasan(self):
        detail = self.detail()
        return detail.ringkasan() if detail else self.get_metode_display()


class PembayaranCash(models.Model):
    pembayaran = models.OneToOneField(Pembayaran, on_delete=models.CASCADE, related_name="pembayarancash")
    uang_dibayar = models.DecimalField(max_digits=12, decimal_places=2)

    def clean(self):
        if self.uang_dibayar is None or self.uang_dibayar < self.pembayaran.total:
            raise ValidationError("Uang dibayar tidak boleh kurang dari total pembayaran.")

    def hitung_kembalian(self):
        return self.uang_dibayar - self.pembayaran.total

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def ringkasan(self):
        return f"Cash — Dibayar {rupiah(self.uang_dibayar)}; Kembalian {rupiah(self.hitung_kembalian())}"


class PembayaranTransfer(models.Model):
    pembayaran = models.OneToOneField(Pembayaran, on_delete=models.CASCADE, related_name="pembayarantransfer")
    nomor_referensi = models.CharField(max_length=100)

    def clean(self):
        if not self.nomor_referensi.strip():
            raise ValidationError("Nomor referensi transfer wajib diisi.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def ringkasan(self):
        return f"Transfer — Referensi {self.nomor_referensi}"


class PembayaranEWallet(models.Model):
    pembayaran = models.OneToOneField(Pembayaran, on_delete=models.CASCADE, related_name="pembayarane_wallet")
    provider = models.CharField(max_length=50)
    nomor_transaksi = models.CharField(max_length=100)

    def clean(self):
        if not self.provider.strip() or not self.nomor_transaksi.strip():
            raise ValidationError("Provider dan nomor transaksi E-Wallet wajib diisi.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def ringkasan(self):
        return f"E-Wallet — {self.provider}; Transaksi {self.nomor_transaksi}"


class PenyimpananPrivat(FileSystemStorage):
    """Bukti pembayaran disimpan DI LUAR MEDIA_ROOT.

    Folder /media/ dilayani publik (lihat bengkel_project/urls.py), padahal
    bukti transfer berisi nama dan rekening pelanggan. Berkasnya hanya bisa
    diambil lewat view pembayaran_bukti_berkas yang memeriksa hak akses.
    Lokasinya dibaca dari settings setiap kali, supaya tes bisa menggantinya.
    """

    @property
    def base_location(self):
        return settings.BUKTI_BAYAR_ROOT

    @property
    def location(self):
        return str(Path(self.base_location).resolve())

    def url(self, name):
        raise ValueError("Bukti pembayaran tidak punya URL publik.")


def pilih_penyimpanan_bukti():
    return PenyimpananPrivat()


class BuktiPembayaran(models.Model):
    """Satu kali pelanggan mengirim bukti transfer bank / e-money (QRIS).

    Bukti yang ditolak tetap disimpan sebagai riwayat; pelanggan mengirim
    bukti baru dari awal. Paling banyak satu bukti MENUNGGU per transaksi.
    Disetujui = Pembayaran dibuat, dan baru saat itulah nota bisa dibuka.
    """

    JENIS_BANK = "BANK"
    JENIS_E_MONEY = "E_MONEY"
    JENIS_CHOICES = [
        (JENIS_BANK, "Transfer Bank"),
        (JENIS_E_MONEY, "E-Money (QRIS)"),
    ]

    STATUS_MENUNGGU = "MENUNGGU"
    STATUS_DISETUJUI = "DISETUJUI"
    STATUS_DITOLAK = "DITOLAK"
    STATUS_CHOICES = [
        (STATUS_MENUNGGU, "Menunggu Verifikasi"),
        (STATUS_DISETUJUI, "Disetujui"),
        (STATUS_DITOLAK, "Ditolak"),
    ]

    transaksi = models.ForeignKey(
        TransaksiServis, on_delete=models.PROTECT, related_name="bukti_pembayaran"
    )
    jenis = models.CharField(max_length=10, choices=JENIS_CHOICES)
    nama_penyedia = models.CharField(max_length=50, verbose_name="Nama bank / e-money")
    nomor_referensi = models.CharField(max_length=100, verbose_name="Nomor referensi / ID transaksi")
    berkas = models.FileField(upload_to="bukti_bayar/%Y/%m/", storage=pilih_penyimpanan_bukti)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_MENUNGGU)
    alasan_tolak = models.TextField(blank=True)
    diunggah_pada = models.DateTimeField(auto_now_add=True)
    diperiksa_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bukti_diperiksa",
    )
    diperiksa_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-diunggah_pada", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["transaksi"], condition=models.Q(status="MENUNGGU"),
                name="satu_bukti_menunggu_per_transaksi",
            ),
        ]

    def __str__(self):
        return f"Bukti {self.transaksi.kode_transaksi} ({self.get_status_display()})"

    @classmethod
    def menunggu_untuk(cls, transaksi):
        return cls.objects.filter(transaksi=transaksi, status=cls.STATUS_MENUNGGU).first()

    @classmethod
    def _pastikan_referensi_belum_dipakai(cls, nama_penyedia, nomor_referensi, kecuali=None):
        """Satu struk transfer/QRIS hanya boleh melunasi satu transaksi."""
        dipakai = cls.objects.filter(
            status=cls.STATUS_DISETUJUI,
            nama_penyedia__iexact=nama_penyedia.strip(),
            nomor_referensi__iexact=nomor_referensi.strip(),
        ).exclude(pk=kecuali)
        if dipakai.exists():
            raise ValidationError("Nomor referensi ini sudah dipakai untuk pembayaran lain.")

    @classmethod
    def ajukan(cls, transaksi, pelanggan, *, jenis, nama_penyedia, nomor_referensi, berkas):
        if transaksi.pelanggan_id != pelanggan.pk:
            raise ValidationError("Transaksi ini bukan milik Anda.")
        if transaksi.status != TransaksiServis.STATUS_SELESAI:
            raise ValidationError("Pembayaran dilakukan setelah servis selesai.")
        if Pembayaran.objects.filter(transaksi=transaksi).exists():
            raise ValidationError("Transaksi ini sudah lunas.")
        if jenis not in dict(cls.JENIS_CHOICES):
            raise ValidationError("Pilih transfer bank atau e-money.")
        if not (nama_penyedia or "").strip() or not (nomor_referensi or "").strip():
            raise ValidationError("Nama bank/e-money dan nomor referensi wajib diisi.")
        if not berkas:
            raise ValidationError("Unggah bukti pembayaran.")
        cls._pastikan_referensi_belum_dipakai(nama_penyedia, nomor_referensi)
        if cls.menunggu_untuk(transaksi):
            raise ValidationError("Bukti sebelumnya masih menunggu verifikasi.")
        try:
            with transaction.atomic():
                return cls.objects.create(
                    transaksi=transaksi, jenis=jenis, nama_penyedia=nama_penyedia.strip(),
                    nomor_referensi=nomor_referensi.strip(), berkas=berkas,
                )
        except IntegrityError:
            # Dua kiriman bersamaan: constraint yang menjaga, pesannya sama.
            raise ValidationError("Bukti sebelumnya masih menunggu verifikasi.")

    def _ambil_keputusan(self, petugas, status, alasan=""):
        """Siapa pun yang memutuskan duluan, dia yang berlaku.

        UPDATE bersyarat status=MENUNGGU: kalau kasir dan admin menekan
        tombol bersamaan, hanya satu baris yang berubah dan yang kedua
        mendapat pesan siapa yang sudah memeriksanya.
        """
        diubah = BuktiPembayaran.objects.filter(pk=self.pk, status=self.STATUS_MENUNGGU).update(
            status=status, alasan_tolak=alasan, diperiksa_oleh=petugas,
            diperiksa_pada=timezone.now(),
        )
        if not diubah:
            terbaru = BuktiPembayaran.objects.select_related("diperiksa_oleh").get(pk=self.pk)
            oleh = terbaru.diperiksa_oleh.nama_tampil if terbaru.diperiksa_oleh else "petugas lain"
            raise ValidationError(
                f"Bukti ini sudah {terbaru.get_status_display().lower()} oleh {oleh}."
            )
        self.refresh_from_db()

    @transaction.atomic
    def setujui(self, petugas):
        # Dicek lagi di sini: dua bukti MENUNGGU bisa membawa referensi yang sama.
        self._pastikan_referensi_belum_dipakai(self.nama_penyedia, self.nomor_referensi, kecuali=self.pk)
        self._ambil_keputusan(petugas, self.STATUS_DISETUJUI)
        if self.jenis == self.JENIS_BANK:
            return Pembayaran.buat(
                self.transaksi, Pembayaran.METODE_TRANSFER, oleh=petugas,
                nomor_referensi=self.nomor_referensi,
            )
        return Pembayaran.buat(
            self.transaksi, Pembayaran.METODE_EWALLET, oleh=petugas,
            provider=self.nama_penyedia, nomor_transaksi=self.nomor_referensi,
        )

    @transaction.atomic
    def tolak(self, petugas, alasan):
        if not (alasan or "").strip():
            raise ValidationError("Alasan penolakan wajib diisi.")
        self._ambil_keputusan(petugas, self.STATUS_DITOLAK, alasan.strip())
