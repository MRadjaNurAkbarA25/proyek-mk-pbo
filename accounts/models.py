from django.contrib.auth.models import AbstractUser
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


class Pelanggan(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil_pelanggan")
    no_telepon = models.CharField(max_length=15, blank=True)
    alamat = models.TextField(blank=True)

    def __str__(self):
        return self.user.username