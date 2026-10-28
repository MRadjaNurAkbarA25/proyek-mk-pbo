from django.shortcuts import render

from accounts.models import Mekanik, Pelanggan, User
from mekanik.models import JenisServis
from servis.models import TransaksiServis

# Data konten landing page. Edit di sini, tidak perlu menyentuh HTML.
LAYANAN = [
    {"ikon": "🚗", "judul": "Servis di Bengkel",
     "deskripsi": "Servis berkala dan perbaikan langsung di bengkel kami, dikerjakan mekanik berpengalaman."},
    {"ikon": "🧰", "judul": "Layanan Panggilan",
     "deskripsi": "Mekanik datang ke lokasi Anda untuk diagnosis awal dan servis ringan (Home Service)."},
    {"ikon": "⚙️", "judul": "Penggantian Suku Cadang",
     "deskripsi": "Suku cadang tersedia dan stoknya tercatat, sehingga pergantian cepat dan transparan."},
    {"ikon": "📋", "judul": "Pengecekan Kendaraan",
     "deskripsi": "Pemeriksaan menyeluruh dengan diagnosis tertulis yang bisa Anda setujui sebelum dikerjakan."},
]

# Alur pemakaian dari sisi pelanggan. Hanya langkah yang memang ada di sistem.
ALUR = [
    {"judul": "Daftar dan catat kendaraan",
     "deskripsi": "Buat akun, lalu tambahkan mobil atau motor Anda ke garasi."},
    {"judul": "Ajukan servis atau panggil mekanik",
     "deskripsi": "Ajukan servis di bengkel dan tunggu persetujuan kasir, atau pesan Home Service dan pilih mekaniknya."},
    {"judul": "Setujui diagnosis",
     "deskripsi": "Mekanik mengirim hasil pemeriksaan dan rincian biaya. Perbaikan baru dimulai setelah Anda setuju."},
    {"judul": "Pantau, lalu bayar",
     "deskripsi": "Ikuti perkembangan servis di linimasa. Bayar transfer atau QRIS langsung dari riwayat servis, atau tunai di kasir, lalu simpan notanya."},
]

# Fitur yang sudah benar-benar ada (FR-31, FR-32, persetujuan diagnosis,
# home service, nota, pembayaran). Jangan menambah fitur yang belum jadi.
ALASAN = [
    {"ikon": "📝", "judul": "Ajukan Servis dari Rumah",
     "deskripsi": "Kirim keluhan dan rencana tanggal datang secara online. Kasir mengonfirmasi, Anda tinggal datang."},
    {"ikon": "📍", "judul": "Pantau Perkembangan Servis",
     "deskripsi": "Setiap tahap tercatat di linimasa, termasuk kabar langsung dari mekanik. Ada tanda kalau ada kabar baru."},
    {"ikon": "✔", "judul": "Biaya Disetujui Lebih Dulu",
     "deskripsi": "Lihat diagnosis dan rincian biaya, lalu putuskan sendiri: setuju atau tolak sebelum perbaikan dimulai."},
    {"ikon": "🏠", "judul": "Pilih Mekanik untuk Home Service",
     "deskripsi": "Tidak sempat ke bengkel? Pilih mekanik yang sedang tersedia dan hubungi langsung selama ia bertugas."},
    {"ikon": "🧾", "judul": "Nota dan Riwayat Tersimpan",
     "deskripsi": "Seluruh riwayat perawatan dan nota pembayaran bisa dibuka kembali kapan saja."},
    {"ikon": "💳", "judul": "Bayar Tunai, Transfer, atau QRIS",
     "deskripsi": "Transfer atau QRIS bisa langsung dari riwayat servis: unggah buktinya, kasir yang memeriksa. "
                  "Tunai dibayar di kasir bengkel, atau ke mekanik saat Home Service."},
]

# Kartu Daftar Harga di landing hanya cuplikan.
HARGA_MAKS = 6


def statistik_bengkel():
    """Statistik nyata dari database untuk landing page; angka 0 tidak ditampilkan."""
    angka = [
        (TransaksiServis.objects.filter(status=TransaksiServis.STATUS_SELESAI).count(), "Servis selesai"),
        (JenisServis.objects.count(), "Jenis layanan"),
        (Mekanik.objects.filter(user__is_active=True).count(), "Mekanik aktif"),
        (Pelanggan.objects.filter(user__is_active=True).count(), "Pelanggan terdaftar"),
    ]
    return [{"angka": nilai, "label": label} for nilai, label in angka if nilai > 0]


def index(request):
    return render(request, "landing/index.html", {
        "layanan": LAYANAN,
        "alur": ALUR,
        "alasan": ALASAN,
        "statistik": statistik_bengkel(),
        "daftar_harga": JenisServis.objects.order_by("harga", "nama_servis")[:HARGA_MAKS],
        "layanan_lainnya": max(JenisServis.objects.count() - HARGA_MAKS, 0),
        # Tombol di hero dan penutup mengarah ke halaman pelanggan kalau yang
        # membuka sudah login sebagai pelanggan; selain itu ke Daftar.
        "pelanggan_login": getattr(request.user, "role", None) == User.ROLE_PELANGGAN,
    })
