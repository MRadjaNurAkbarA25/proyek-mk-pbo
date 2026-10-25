"""Isi awal FAQ (FR-34), dipakai oleh `manage.py seed_demo`.

Isinya ditulis dari perilaku aplikasi yang sebenarnya. Setelah masuk database,
admin mengubahnya lewat menu Kelola FAQ, bukan lewat berkas ini.
"""
from .models import PertanyaanFAQ as F

S, H, P, A = F.KATEGORI_SERVIS, F.KATEGORI_HOME_SERVICE, F.KATEGORI_PEMBAYARAN, F.KATEGORI_AKUN

# (kategori, pertanyaan, jawaban, kata_kunci)  -- urutan tampil = urutan di daftar ini
FAQ_AWAL = [
    # ---- Servis dan Pengajuan ----
    (S, "Bagaimana cara mengajukan servis di bengkel?",
     "Login sebagai pelanggan, buka menu Ajukan Servis, pilih kendaraan, tulis keluhannya, lalu kirim. "
     "Tanggal rencana datang boleh dikosongkan. Pengajuan Anda akan ditinjau kasir.",
     "ajukan pengajuan servis service servise booking daftar bengkel keluhan"),
    (S, "Berapa lama waktu pengerjaan servis?",
     "Perkiraannya: ganti oli sekitar 30 menit, ganti ban 45 menit, servis rem 1 jam, tune up 1,5 jam, "
     "dan servis AC 2 jam. Waktu pastinya tergantung hasil diagnosis mekanik.",
     "lama durasi waktu estimasi selesai berapa jam menit rem oli ban tune ac servis service servise"),
    (S, "Berapa lama kendaraan boleh datang setelah pengajuan diterima?",
     "Kendaraan harus tiba paling lambat 3 hari sejak pengajuan diterima kasir, atau sejak tanggal rencana "
     "datang bila tanggalnya lebih belakangan. Lewat dari itu, transaksi dibatalkan otomatis dan Anda perlu "
     "mengajukan servis lagi.",
     "batas kedatangan datang tiba terlambat hangus batal otomatis hari tanggal rencana"),
    (S, "Bagaimana cara membatalkan pengajuan servis?",
     "Buka menu Ajukan Servis, lihat daftar pengajuan Anda, lalu pilih Batalkan. Pembatalan hanya bisa "
     "dilakukan selama pengajuan belum diproses kasir.",
     "batal batalkan pengajuan cancel hapus tarik"),
    (S, "Bagaimana cara menyetujui atau menolak diagnosis mekanik?",
     "Setelah memeriksa kendaraan, mekanik menulis diagnosis dan rencana perbaikan. Buka menu Persetujuan "
     "Diagnosis untuk membacanya, lalu pilih setuju atau tolak. Perbaikan baru dimulai setelah Anda setuju; "
     "kalau ditolak, servis dibatalkan. Perkembangannya bisa dipantau di Riwayat Servis.",
     "diagnosis persetujuan setuju tolak konfirmasi mekanik perbaikan riwayat status pantau"),
    (S, "Bagaimana cara mendaftarkan kendaraan saya?",
     "Buka menu Kendaraan Saya, pilih tambah kendaraan, tentukan jenisnya (mobil atau motor), lalu isi "
     "datanya seperti nomor polisi, merek, model, dan tahun. Kendaraan harus terdaftar sebelum bisa "
     "diajukan servis.",
     "kendaraan mobil motor tambah daftarkan nomor polisi plat garasi"),

    # ---- Home Service ----
    (H, "Apa itu Home Service?",
     "Home Service adalah layanan mekanik datang ke lokasi Anda untuk diagnosis awal dan servis ringan, "
     "jadi Anda tidak perlu membawa kendaraan ke bengkel.",
     "home service panggil panggilan rumah lokasi datang mekanik layanan"),
    (H, "Bagaimana cara memesan Home Service?",
     "Buka menu Pesan Home Service, pilih kendaraan, pilih mekanik yang berstatus tersedia, isi alamat "
     "lokasi dan keluhan, lalu kirim. Pesanan baru berjalan setelah mekanik menerima permintaan Anda.",
     "pesan home service panggil mekanik rumah alamat lokasi booking"),
    (H, "Apa yang terjadi setelah saya memesan Home Service?",
     "Pesanan menunggu mekanik menerima. Setelah diterima, mekanik datang ke lokasi, menulis diagnosis, "
     "dan Anda menyetujuinya seperti pada servis di bengkel. Statusnya bisa dilihat di Riwayat Servis. "
     "Kalau terasa terlalu lama, hubungi bengkel lewat WhatsApp.",
     "home service status menunggu diterima mekanik datang lama proses"),

    # ---- Pembayaran ----
    (P, "Metode pembayaran apa saja yang tersedia?",
     "Pembayaran bisa dilakukan secara tunai, transfer, atau e-wallet. Pembayaran diproses oleh kasir "
     "setelah servis selesai.",
     "bayar pembayaran metode tunai cash transfer bank ewallet e-wallet dana ovo gopay cara"),
    (P, "Bagaimana cara melihat nota pembayaran?",
     "Buka menu Riwayat Servis, pilih servis yang sudah dibayar, lalu klik Lihat Nota Pembayaran. Nota "
     "baru muncul setelah kasir mencatat pembayaran.",
     "nota struk bukti kuitansi pembayaran lihat cetak print"),
    (P, "Berapa biaya servis dan kapan saya membayar?",
     "Biaya dihitung dari layanan dan sparepart yang dicatat mekanik selama pengerjaan, dan totalnya "
     "tertera di detail servis. Anda membayar di kasir setelah servis berstatus Selesai.",
     "biaya harga tarif total bayar berapa mahal kapan sparepart ongkos"),

    # ---- Akun ----
    (A, "Bagaimana cara mendaftar akun?",
     "Klik Sign Up di halaman depan, isi nama lengkap, e-mail, nomor telepon (boleh dikosongkan), dan "
     "kata sandi, lalu kirim. Setelah itu Anda bisa login.",
     "daftar registrasi register sign up buat akun baru"),
    (A, "Saya lupa kata sandi, bagaimana cara mengatasinya?",
     "Di halaman login, klik Lupa kata sandi? lalu ikuti petunjuknya. Kalau cara itu tidak tersedia, "
     "hubungi bengkel agar admin membantu mengganti kata sandi Anda.",
     "lupa sandi password kata sandi reset ganti ubah login masuk"),
    (A, "Bagaimana cara mengubah data profil dan nomor telepon?",
     "Setelah login, buka menu Profil Saya, ubah data yang diperlukan, lalu simpan.",
     "profil ubah edit nomor telepon nama email data akun foto"),
]


def isi_faq_awal():
    """Tambahkan FAQ awal yang belum ada; mengembalikan jumlah yang baru dibuat.

    Aman dijalankan berulang, dan TIDAK menimpa FAQ yang sudah diubah admin:
    pengenalnya (kategori, pertanyaan), bukan isinya.
    """
    baru = 0
    for urutan, (kategori, pertanyaan, jawaban, kata_kunci) in enumerate(FAQ_AWAL, start=1):
        _, dibuat = F.objects.get_or_create(
            kategori=kategori, pertanyaan=pertanyaan,
            defaults={"jawaban": jawaban, "kata_kunci": kata_kunci, "urutan": urutan},
        )
        baru += dibuat
    return baru
