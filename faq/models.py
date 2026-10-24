"""FR-34: FAQ chat. Chatbot berbasis aturan, tanpa AI.

Semua logika pencocokan ada di sini (bukan di JavaScript) supaya bisa diuji.
JavaScript hanya menampilkan hasilnya sebagai gelembung chat.
"""
import re

from django.db import models

# Kata yang terlalu umum untuk dijadikan dasar pencocokan.
KATA_UMUM = {"saya", "apa", "bagaimana", "cara", "yang", "di", "ke", "dan", "bisa"}


def kata_penting(teks):
    """Himpunan kata bermakna dari sebuah teks: huruf kecil, tanpa tanda baca
    dan tanpa KATA_UMUM. "Servis rem?" dan "servis rem" dianggap sama."""
    return {k for k in re.findall(r"\w+", (teks or "").lower()) if k not in KATA_UMUM}


class PertanyaanFAQ(models.Model):
    KATEGORI_SERVIS = "SERVIS"
    KATEGORI_HOME_SERVICE = "HOME_SERVICE"
    KATEGORI_PEMBAYARAN = "PEMBAYARAN"
    KATEGORI_AKUN = "AKUN"
    # Urutan di sini = urutan tombol kategori di jendela chat.
    KATEGORI_CHOICES = [
        (KATEGORI_SERVIS, "Servis dan Pengajuan"),
        (KATEGORI_HOME_SERVICE, "Home Service"),
        (KATEGORI_PEMBAYARAN, "Pembayaran"),
        (KATEGORI_AKUN, "Akun"),
    ]

    kategori = models.CharField(max_length=20, choices=KATEGORI_CHOICES)
    pertanyaan = models.CharField(max_length=200)
    jawaban = models.TextField()
    kata_kunci = models.CharField(
        max_length=255, blank=True,
        help_text="Kata lain yang mungkin diketik pengunjung, dipisah spasi. "
                  "Contoh: servis service servise",
    )
    urutan = models.PositiveIntegerField(
        default=0, help_text="Angka kecil tampil lebih dulu di dalam kategorinya.",
    )
    # FAQ tidak dihapus, hanya dinonaktifkan (tidak tampil di chat).
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["urutan", "id"]
        verbose_name = "pertanyaan FAQ"
        verbose_name_plural = "pertanyaan FAQ"

    def __str__(self):
        return self.pertanyaan

    # --- pencocokan kata kunci -------------------------------------------
    def skor_kecocokan(self, teks):
        """Jumlah kata penting dari `teks` yang juga ada di pertanyaan atau kata kunci FAQ ini."""
        kata_faq = kata_penting(self.pertanyaan + " " + self.kata_kunci)
        return len(kata_penting(teks) & kata_faq)

    @classmethod
    def cari(cls, teks, batas=3):
        """Sampai `batas` FAQ aktif dengan skor tertinggi. Skor 0 tidak ikut.
        Skor sama: urutan tampil (urutan, id) menentukan, karena sorted() stabil."""
        hasil = [(f.skor_kecocokan(teks), f) for f in cls.objects.filter(aktif=True)]
        return [f for skor, f in sorted(hasil, key=lambda x: -x[0]) if skor > 0][:batas]

    # --- aktif / nonaktif ------------------------------------------------
    def nonaktifkan(self):
        self.aktif = False
        self.save(update_fields=["aktif"])

    def aktifkan(self):
        self.aktif = True
        self.save(update_fields=["aktif"])

    def sebagai_dict(self):
        """Bentuk yang dikirim ke jendela chat. kata_kunci sengaja tidak ikut."""
        return {"id": self.pk, "pertanyaan": self.pertanyaan, "jawaban": self.jawaban}

    @classmethod
    def kategori_aktif(cls):
        """[{kode, nama, pertanyaan: [...]}] untuk kategori yang punya FAQ aktif,
        urut seperti KATEGORI_CHOICES."""
        per_kategori = {}
        for f in cls.objects.filter(aktif=True):
            per_kategori.setdefault(f.kategori, []).append(f.sebagai_dict())
        return [
            {"kode": kode, "nama": nama, "pertanyaan": per_kategori[kode]}
            for kode, nama in cls.KATEGORI_CHOICES if kode in per_kategori
        ]
