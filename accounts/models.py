from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = "ADMIN"
    ROLE_KASIR = "KASIR"
    ROLE_MEKANIK = "MEKANIK"
    ROLE_PELANGGAN = "PELANGGAN"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_KASIR, "Kasir"),
        (ROLE_MEKANIK, "Mekanik"),
        (ROLE_PELANGGAN, "Pelanggan"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Mekanik(models.Model):
    STATUS_TERSEDIA = "TERSEDIA"
    STATUS_SEDANG_SERVIS = "SEDANG_SERVIS"
    STATUS_CUTI = "CUTI"

    STATUS_CHOICES = [
        (STATUS_TERSEDIA, "Tersedia"),
        (STATUS_SEDANG_SERVIS, "Sedang Servis"),
        (STATUS_CUTI, "Cuti"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil_mekanik")
    spesialisasi = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TERSEDIA)

    def __str__(self):
        return self.user.username

    # ---- Perilaku Mekanik (encapsulation): status dikelola lewat method ----
    @property
    def jumlah_servis(self):
        """Jumlah servis yang sudah selesai (atribut jumlahServis di diagram kelas)."""
        from servis.models import TransaksiServis
        return self.transaksi_servis.filter(status=TransaksiServis.STATUS_SELESAI).count()

    @property
    def bisa_menerima_pekerjaan(self):
        return self.status == self.STATUS_TERSEDIA

    def punya_pekerjaan_berjalan(self):
        """True jika sedang mengerjakan kendaraan, atau punya home service yang sudah diterima."""
        from servis.models import TransaksiServis as T
        sedang_dikerjakan = Q(status=T.STATUS_DIKERJAKAN)
        home_service_diterima = Q(
            tipe_layanan=T.TIPE_HOME_SERVICE,
            status__in=[T.STATUS_MENUNGGU, T.STATUS_MENUNGGU_KONFIRMASI],
        )
        return self.transaksi_servis.filter(sedang_dikerjakan | home_service_diterima).exists()

    def perbarui_status_otomatis(self):
        """Sinkronkan status TERSEDIA <-> SEDANG_SERVIS. Status CUTI tidak disentuh."""
        self.refresh_from_db(fields=["status"])
        if self.status == self.STATUS_CUTI:
            return
        baru = self.STATUS_SEDANG_SERVIS if self.punya_pekerjaan_berjalan() else self.STATUS_TERSEDIA
        if baru != self.status:
            self.status = baru
            self.save(update_fields=["status"])

    def ubah_ketersediaan(self, status_baru):
        """FR-9: mekanik hanya boleh memilih TERSEDIA/CUTI; SEDANG_SERVIS diatur sistem."""
        if status_baru not in (self.STATUS_TERSEDIA, self.STATUS_CUTI):
            raise ValidationError("Status hanya bisa diubah ke Tersedia atau Cuti.")
        if self.punya_pekerjaan_berjalan():
            raise ValidationError("Status otomatis 'Sedang Servis' selama ada pekerjaan berjalan.")
        self.status = status_baru
        self.save(update_fields=["status"])


class Pelanggan(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil_pelanggan")
    no_telepon = models.CharField(max_length=15, blank=True)
    alamat = models.TextField(blank=True)

    def __str__(self):
        return self.user.username