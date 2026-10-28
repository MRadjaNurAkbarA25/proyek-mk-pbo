"""FR-34: FAQ chat berbasis aturan, tanpa AI; pencocokan di Python (faq/pencocokan.py) agar bisa diuji."""
import re

from django.db import models

from . import pencocokan


def isi_placeholder(teks, data):
    """Ganti {nama} di jawaban dengan data Info Bengkel. Nama yang tidak
    dikenal (atau nilainya bukan teks) dibiarkan apa adanya."""
    def ganti(m):
        nilai = data.get(m.group(1))
        if isinstance(nilai, str):
            return nilai
        if m.group(1) == "jam_buka" and nilai:
            return "; ".join(f"{hari} {jam}" for hari, jam in nilai)
        if isinstance(nilai, dict) and {"bank", "nomor", "atas_nama"} <= nilai.keys():
            return f"{nilai['bank']} {nilai['nomor']} a.n. {nilai['atas_nama']}"
        return m.group(0)
    return re.sub(r"\{(\w+)\}", ganti, teks)


def info_bengkel():
    # Satu sumber data bengkel, sama dengan yang dipakai semua template.
    from landing.context_processors import info_bengkel as info
    return info(None)


class PertanyaanFAQ(models.Model):
    KATEGORI_SERVIS = "SERVIS"
    KATEGORI_HOME_SERVICE = "HOME_SERVICE"
    KATEGORI_KENDARAAN = "KENDARAAN"
    KATEGORI_PEMBAYARAN = "PEMBAYARAN"
    KATEGORI_BIAYA = "BIAYA"
    KATEGORI_AKUN = "AKUN"
    KATEGORI_INFO = "INFO"
    # Urutan di sini = urutan tombol kategori di jendela chat.
    KATEGORI_CHOICES = [
        (KATEGORI_SERVIS, "Servis di Bengkel"),
        (KATEGORI_HOME_SERVICE, "Home Service"),
        (KATEGORI_KENDARAAN, "Kendaraan"),
        (KATEGORI_PEMBAYARAN, "Pembayaran"),
        (KATEGORI_BIAYA, "Biaya dan Sparepart"),
        (KATEGORI_AKUN, "Akun"),
        (KATEGORI_INFO, "Info Bengkel"),
    ]

    kategori = models.CharField(max_length=20, choices=KATEGORI_CHOICES)
    pertanyaan = models.CharField(max_length=200)
    jawaban = models.TextField(
        help_text="Boleh memakai {alamat_bengkel}, {jam_buka}, {telepon_bengkel}, {email_bengkel}; "
                  "diisi otomatis dari data bengkel.",
    )
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

    # --- pencocokan --------------------------------------------------------
    @classmethod
    def cari_lengkap(cls, teks, batas=3):
        """([(faq, skor), ...] maksimal `batas`, yakin). Skor 0 tidak ikut.
        Skor sama: urutan tampil (urutan, id) menentukan, karena sorted() stabil."""
        semua = list(cls.objects.filter(aktif=True))
        skor = pencocokan.nilai(teks, [(f.pertanyaan, f.kata_kunci) for f in semua])
        hasil = [(f, s) for f, s in sorted(zip(semua, skor), key=lambda x: -x[1]) if s > 0][:batas]
        return hasil, pencocokan.yakin([s for _, s in hasil])

    @classmethod
    def cari(cls, teks, batas=3):
        return [f for f, _ in cls.cari_lengkap(teks, batas)[0]]

    @classmethod
    def token_ketikan(cls, teks):
        """Kata yang dikenali dari ketikan, setelah koreksi salah ketik (untuk admin)."""
        kosakata = set()
        for f in cls.objects.filter(aktif=True):
            kosakata.update(pencocokan.token(f.pertanyaan), pencocokan.token(f.kata_kunci))
        return pencocokan.token(teks, kosakata)

    # --- aktif / nonaktif ------------------------------------------------
    def nonaktifkan(self):
        self.aktif = False
        self.save(update_fields=["aktif"])

    def aktifkan(self):
        self.aktif = True
        self.save(update_fields=["aktif"])

    def sebagai_dict(self, info=None):
        """Bentuk yang dikirim ke jendela chat. kata_kunci sengaja tidak ikut."""
        jawaban = isi_placeholder(self.jawaban, info if info is not None else info_bengkel())
        return {"id": self.pk, "pertanyaan": self.pertanyaan, "jawaban": jawaban}

    @classmethod
    def kategori_aktif(cls):
        """[{kode, nama, pertanyaan: [...]}] untuk kategori yang punya FAQ aktif,
        urut seperti KATEGORI_CHOICES."""
        info = info_bengkel()
        per_kategori = {}
        for f in cls.objects.filter(aktif=True):
            per_kategori.setdefault(f.kategori, []).append(f.sebagai_dict(info))
        return [
            {"kode": kode, "nama": nama, "pertanyaan": per_kategori[kode]}
            for kode, nama in cls.KATEGORI_CHOICES if kode in per_kategori
        ]
