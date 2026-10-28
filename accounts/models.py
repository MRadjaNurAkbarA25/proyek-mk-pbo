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

    JK_LAKI = "L"
    JK_PEREMPUAN = "P"
    JK_CHOICES = [(JK_LAKI, "Laki-laki"), (JK_PEREMPUAN, "Perempuan")]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Data pribadi dipakai bersama oleh keempat role lewat halaman Profil Saya.
    no_telepon = models.CharField(max_length=20, blank=True, verbose_name="Nomor WhatsApp / HP")
    alamat = models.TextField(blank=True, verbose_name="Alamat domisili lengkap")
    # Titik alamat dari peta (OpenStreetMap); mengisi awal form Home Service.
    alamat_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    alamat_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    jenis_kelamin = models.CharField(max_length=1, choices=JK_CHOICES, blank=True)
    # FileField, bukan ImageField, supaya proyek tidak butuh paket Pillow.
    # Ekstensi divalidasi di ProfilForm.
    foto = models.FileField(upload_to="foto_profil/", blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def nama_tampil(self):
        return self.get_full_name() or self.username

    @property
    def profil_lengkap(self):
        """Alamat dan nomor telepon terisi - syarat memakai fitur Home Service."""
        return bool(self.alamat.strip() and self.no_telepon.strip())

    # ------------------------------------------------------------------
    # Menonaktifkan akun, alih-alih menghapus
    # ------------------------------------------------------------------
    # Relasi riwayat memakai SET_NULL, jadi menghapus kasir/mekanik menghapus
    # jejaknya; akun nonaktif tidak bisa login tapi jejaknya utuh. Admin tidak
    # bisa dinonaktifkan supaya bengkel tidak terkunci tanpa admin.
    ROLE_BISA_DINONAKTIFKAN = (ROLE_KASIR, ROLE_MEKANIK)

    def alasan_tidak_bisa_dinonaktifkan(self):
        if self.role not in self.ROLE_BISA_DINONAKTIFKAN:
            return "Hanya akun kasir dan mekanik yang bisa dinonaktifkan dari sini."
        if self.role == self.ROLE_MEKANIK:
            profil = getattr(self, "profil_mekanik", None)
            if profil is not None and profil.jumlah_pekerjaan_belum_tuntas():
                return (
                    "Mekanik ini masih memegang pekerjaan yang belum selesai. "
                    "Selesaikan atau alihkan dulu pekerjaannya."
                )
        return None

    def nonaktifkan(self):
        alasan = self.alasan_tidak_bisa_dinonaktifkan()
        if alasan:
            raise ValidationError(alasan)
        self.is_active = False
        self.save(update_fields=["is_active"])
        profil = getattr(self, "profil_mekanik", None)
        if profil is not None:
            # Cuti tidak pernah diubah perbarui_status_otomatis(), jadi mekanik
            # nonaktif tidak akan muncul lagi di pilihan home service.
            profil.status = Mekanik.STATUS_CUTI
            profil.save(update_fields=["status"])

    def aktifkan(self):
        if self.role not in self.ROLE_BISA_DINONAKTIFKAN:
            raise ValidationError("Hanya akun kasir dan mekanik yang dikelola dari sini.")
        self.is_active = True
        self.save(update_fields=["is_active"])
        profil = getattr(self, "profil_mekanik", None)
        if profil is not None:
            profil.status = Mekanik.STATUS_TERSEDIA
            profil.save(update_fields=["status"])
            profil.perbarui_status_otomatis()


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

    def jumlah_pekerjaan_belum_tuntas(self):
        """Transaksi mekanik yang belum Selesai/Dibatalkan, termasuk panggilan yang belum dijawab.

        Dipakai sebelum menonaktifkan akun.
        """
        from servis.models import TransaksiServis as T
        return self.transaksi_servis.filter(status__in=T.STATUS_AKTIF).count()

    def alasan_tidak_bisa_dihapus(self):
        """Mekanik yang pernah memegang transaksi tidak boleh dihapus (namanya hilang dari riwayat).

        Mekanik tanpa riwayat boleh dihapus; yang lain dinonaktifkan (User.nonaktifkan).
        """
        jumlah = self.transaksi_servis.count()
        if jumlah:
            return (
                f"Mekanik ini punya riwayat {jumlah} transaksi, jadi tidak dihapus "
                "supaya namanya tetap tercatat di riwayat dan laporan. "
                "Nonaktifkan akunnya bila sudah tidak bekerja."
            )
        return None

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
    # no_telepon dan alamat ada di model User agar dipakai bersama keempat role.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil_pelanggan")

    def __str__(self):
        return self.user.username