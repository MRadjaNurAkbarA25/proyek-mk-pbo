from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, models, transaction

from servis.models import TransaksiServis


class Pembayaran(models.Model):
    METODE_CASH = "CASH"
    METODE_TRANSFER = "TRANSFER"
    METODE_EWALLET = "E_WALLET"
    METODE_CHOICES = [
        (METODE_CASH, "Cash"),
        (METODE_TRANSFER, "Transfer"),
        (METODE_EWALLET, "E-Wallet"),
    ]

    transaksi = models.OneToOneField(
        TransaksiServis, on_delete=models.PROTECT, related_name="pembayaran"
    )
    tanggal = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    metode = models.CharField(max_length=20, choices=METODE_CHOICES)

    def __str__(self):
        return f"Pembayaran {self.transaksi.kode_transaksi}"

    @classmethod
    def buat(cls, transaksi, metode, **data):
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
                    transaksi=transaksi, total=transaksi.total_biaya, metode=metode
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
        return f"Cash — Dibayar Rp {self.uang_dibayar:,.0f}; Kembalian Rp {self.hitung_kembalian():,.0f}"


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
