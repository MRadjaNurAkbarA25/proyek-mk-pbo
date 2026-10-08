from django.shortcuts import render

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

ALASAN = [
    {"ikon": "✔", "judul": "Kendali Sepenuhnya di Tangan Anda",
     "deskripsi": "Lihat diagnosis mekanik dan putuskan sendiri: setuju atau tolak sebelum perbaikan dimulai."},
    {"ikon": "🏠", "judul": "Praktis dengan Home Service",
     "deskripsi": "Tidak sempat ke bengkel? Panggil mekanik yang sedang tersedia ke lokasi Anda."},
    {"ikon": "🕘", "judul": "Riwayat Servis Terintegrasi",
     "deskripsi": "Seluruh riwayat perawatan kendaraan tersimpan rapi dan bisa dibuka kapan saja."},
    {"ikon": "💳", "judul": "Pembayaran Mudah dan Cepat",
     "deskripsi": "Bayar tunai, transfer, atau e-wallet, lengkap dengan nota yang jelas."},
    {"ikon": "🔧", "judul": "Ditangani Mekanik Spesialis",
     "deskripsi": "Setiap pekerjaan dipegang mekanik sesuai spesialisasinya."},
]


def index(request):
    return render(request, "landing/index.html", {"layanan": LAYANAN, "alasan": ALASAN})
