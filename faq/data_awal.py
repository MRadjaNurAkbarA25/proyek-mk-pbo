"""Isi awal FAQ (FR-34) untuk `seed_demo`; setelah di database, admin mengubahnya lewat Kelola FAQ.

{placeholder} diisi dari landing.context_processors.info_bengkel saat jawaban dikirim.
"""
from .models import PertanyaanFAQ as F

S, H, K = F.KATEGORI_SERVIS, F.KATEGORI_HOME_SERVICE, F.KATEGORI_KENDARAAN
P, B, A, I = F.KATEGORI_PEMBAYARAN, F.KATEGORI_BIAYA, F.KATEGORI_AKUN, F.KATEGORI_INFO

# (kategori, pertanyaan, jawaban, kata_kunci)  -- urutan tampil = urutan di daftar ini
FAQ_AWAL = [
    # ---- Servis di Bengkel ----
    (S, "Bagaimana cara mengajukan servis di bengkel?",
     "Login sebagai pelanggan, buka menu Ajukan Servis, pilih kendaraan, tulis keluhannya, lalu kirim. "
     "Tanggal rencana datang boleh dikosongkan. Pengajuan Anda akan ditinjau kasir; setelah diterima, "
     "bawa kendaraan ke bengkel.",
     "ajukan pengajuan servis service servise srvis booking bengkel keluhan motor mobil kendaraan bawa"),
    (S, "Berapa lama waktu pengerjaan servis?",
     "Perkiraan waktu tiap layanan, misalnya ganti oli, servis rem, ganti ban, tune up, atau servis AC, "
     "tertera di Daftar Harga di halaman depan. Waktu pastinya tergantung hasil diagnosis mekanik.",
     "durasi waktu estimasi lama selesai jam menit rem oli ban tune ac pengerjaan kerja"),
    (S, "Berapa lama kendaraan boleh datang setelah pengajuan diterima?",
     "Kendaraan harus tiba paling lambat 3 hari sejak pengajuan diterima kasir, atau sejak tanggal rencana "
     "datang bila tanggalnya lebih belakangan. Lewat dari itu, transaksi dibatalkan otomatis dan Anda perlu "
     "mengajukan servis lagi.",
     "batas datang tiba terlambat telat hangus batal otomatis hari tanggal 3 tiga"),
    (S, "Bagaimana cara membatalkan pengajuan servis?",
     "Buka menu Ajukan Servis, lihat daftar pengajuan Anda, lalu pilih Batalkan. Pembatalan hanya bisa "
     "dilakukan selama pengajuan belum diproses kasir.",
     "batal batalkan cancel tarik pengajuan urung"),
    (S, "Bisakah saya mengubah tanggal rencana datang?",
     "Bisa. Di daftar pengajuan Anda (menu Ajukan Servis), ubah tanggal rencana datang selama kendaraan "
     "belum tiba di bengkel. Batas 3 hari dihitung dari tanggal yang lebih belakangan.",
     "ubah ganti geser undur tanggal rencana datang jadwal hari"),
    (S, "Kenapa pengajuan servis saya ditolak?",
     "Kasir wajib menulis alasan saat menolak pengajuan. Alasannya bisa dilihat di daftar pengajuan Anda "
     "(menu Ajukan Servis). Setelah itu Anda boleh mengajukan servis lagi.",
     "tolak ditolak alasan pengajuan kasir"),
    (S, "Kenapa kendaraan saya tidak bisa diajukan servis?",
     "Satu kendaraan hanya boleh punya satu proses berjalan. Kendaraan yang masih punya pengajuan yang "
     "menunggu kasir, atau servis yang belum selesai, tidak bisa diajukan lagi sampai proses itu selesai.",
     "ajukan kendaraan motor mobil sedang proses diproses berjalan dobel pilih"),
    (S, "Bagaimana cara menyetujui atau menolak diagnosis mekanik?",
     "Setelah memeriksa kendaraan, mekanik menulis diagnosis dan rincian biaya. Buka menu Persetujuan "
     "Diagnosis untuk membacanya, lalu pilih setuju atau tolak. Perbaikan baru dimulai setelah Anda setuju; "
     "kalau ditolak, servis dibatalkan. Ada tanda angka di menu itu bila ada diagnosis yang menunggu Anda.",
     "diagnosis setuju persetujuan tolak konfirmasi mekanik perbaikan rincian"),
    (S, "Apa arti status servis saya?",
     "Menunggu: kendaraan menunggu diperiksa mekanik. Menunggu Konfirmasi Mekanik: pesanan Home Service "
     "menunggu diterima mekanik. Menunggu Konfirmasi Pelanggan: diagnosis menunggu persetujuan Anda. "
     "Dikerjakan: perbaikan sedang berjalan. Selesai: servis selesai dan bisa dibayar. Dibatalkan: servis "
     "tidak dilanjutkan.",
     "arti status menunggu konfirmasi dikerjakan selesai dibatalkan maksud keterangan"),
    (S, "Bagaimana cara memantau perkembangan servis?",
     "Buka menu Riwayat Servis lalu pilih servisnya. Bagian Perkembangan Servis (linimasa) mencatat setiap "
     "tahap, termasuk kabar dari mekanik. Menu Riwayat Servis menampilkan tanda angka bila ada kabar baru "
     "yang belum Anda baca.",
     "pantau perkembangan progres linimasa kabar update riwayat status lacak"),
    (S, "Bagaimana cara bertanya ke mekanik yang menangani servis saya?",
     "Di detail servis (menu Riwayat Servis) ada kotak pesan di bagian Perkembangan Servis. Pesan hanya "
     "bisa dikirim selama servis sedang dipegang mekanik dan belum selesai, dan tidak bisa diubah setelah "
     "dikirim. Mekanik membalas lewat kabar di linimasa.",
     "tanya mekanik pesan kirim pertanyaan linimasa chat"),

    # ---- Home Service ----
    (H, "Apa itu Home Service?",
     "Home Service adalah layanan mekanik datang ke lokasi Anda untuk diagnosis awal dan servis ringan, "
     "jadi Anda tidak perlu membawa kendaraan ke bengkel.",
     "home service panggil panggilan rumah lokasi mekanik datang"),
    (H, "Bagaimana cara memesan Home Service?",
     "Buka menu Pesan Home Service, pilih kendaraan, pilih mekanik yang berstatus tersedia, isi alamat "
     "lokasi dan keluhan, lalu kirim. Pesanan baru berjalan setelah mekanik menerima permintaan Anda.",
     "pesan home service panggil booking order caranya"),
    (H, "Bagaimana memilih mekanik untuk Home Service?",
     "Saat memesan Home Service, daftar pilihan mekanik hanya berisi mekanik yang sedang berstatus "
     "tersedia. Kalau tidak ada yang bisa dipilih, semua mekanik sedang sibuk; coba lagi nanti atau "
     "ajukan servis di bengkel.",
     "pilih mekanik tersedia kosong sibuk home service"),
    (H, "Apa yang terjadi setelah saya memesan Home Service?",
     "Pesanan berstatus Menunggu Konfirmasi Mekanik sampai mekanik menerimanya. Setelah diterima, mekanik "
     "menuju lokasi, memeriksa kendaraan, lalu menulis diagnosis yang Anda setujui seperti servis di "
     "bengkel. Semua tahapnya tercatat di Riwayat Servis.",
     "setelah pesan home service lanjut proses tahap"),
    (H, "Mekanik Home Service belum menerima pesanan atau belum datang, bagaimana?",
     "Selama berstatus Menunggu Konfirmasi Mekanik, pesanan masih menunggu jawaban mekanik. Kalau mekanik "
     "menolak, pesanan dibatalkan dan Anda bisa memesan lagi dengan mekanik lain. Kalau terasa terlalu "
     "lama, hubungi bengkel di {telepon_bengkel}.",
     "belum terima datang lama tunggu menunggu konfirmasi mekanik tolak home service"),
    (H, "Bagaimana cara menghubungi mekanik Home Service?",
     "Setelah mekanik menerima pesanan Home Service dan selama pekerjaannya belum selesai, nomor mekanik "
     "beserta tombol WhatsApp dan telepon tampil di detail servis (menu Riwayat Servis). Di luar itu, "
     "hubungi nomor resmi bengkel.",
     "kontak hubungi nomor mekanik whatsapp telepon home service"),
    (H, "Apa yang terjadi jika Home Service harus dilanjutkan di bengkel?",
     "Bila perbaikan tidak bisa selesai di lokasi, mekanik mengalihkannya ke bengkel dan menyepakati "
     "tanggal kendaraan dibawa. Setelah itu berlaku aturan servis di bengkel, termasuk batas kedatangan "
     "3 hari.",
     "lanjut bengkel alih pindah bawa home service"),

    # ---- Kendaraan ----
    (K, "Bagaimana cara mendaftarkan kendaraan saya?",
     "Buka menu Kendaraan Saya, pilih tambah kendaraan, tentukan jenisnya (mobil atau motor), lalu isi "
     "datanya seperti nomor polisi, merek, model, dan tahun pembuatan (lihat STNK). Kendaraan harus "
     "terdaftar sebelum bisa diajukan servis.",
     "tambah daftarkan kendaraan mobil motor nomor polisi garasi"),
    (K, "Bagaimana cara mengubah data kendaraan?",
     "Buka menu Kendaraan Saya, pilih kendaraannya, lalu klik ubah. Data seperti nomor polisi, merek, "
     "model, dan tahun pembuatan bisa diperbaiki di sana.",
     "ubah edit data kendaraan nopol salah merek model tahun pembuatan stnk"),
    (K, "Kenapa kendaraan saya tidak bisa dihapus?",
     "Kendaraan yang sudah pernah diservis tidak bisa dihapus, karena riwayat servis dan tagihannya adalah "
     "catatan bengkel. Kendaraan yang belum pernah diservis bisa dihapus dari menu Kendaraan Saya.",
     "hapus delete kendaraan motor mobil riwayat"),
    (K, "Apa bedanya mendaftarkan mobil dan motor?",
     "Jenis kendaraan dipilih saat menambah kendaraan. Mobil diisi jumlah pintu dan jenis mobil (misalnya "
     "SUV atau MPV); motor diisi jenis motor (misalnya matic) dan kapasitas mesin. Data lainnya sama.",
     "beda mobil motor jenis pintu cc kapasitas mesin"),

    # ---- Pembayaran ----
    (P, "Metode pembayaran apa saja yang tersedia?",
     "Tunai, transfer bank, atau e-money lewat QRIS. Transfer dan QRIS bisa Anda bayar sendiri dari detail "
     "servis di Riwayat Servis. Tunai dibayar di kasir bengkel, atau ke mekanik untuk Home Service.",
     "metode bayar tunai transfer qris bank pilihan"),
    (P, "Kapan saya harus membayar servis?",
     "Pembayaran dilakukan setelah servis berstatus Selesai. Sebelum itu tombol bayar belum muncul.",
     "kapan bayar waktu selesai"),
    (P, "Bagaimana cara membayar lewat transfer atau QRIS?",
     "Buka Riwayat Servis, pilih servis yang sudah Selesai, lalu klik Bayar Transfer / QRIS. Pindai QRIS "
     "atau transfer ke rekening yang tertera sebesar total tagihan, lalu kirim bukti pembayaran beserta "
     "nama bank/e-money dan nomor referensinya.",
     "bayar transfer qris rekening scan bank"),
    (P, "Bukti pembayaran seperti apa yang diterima?",
     "Foto atau tangkapan layar (JPG, PNG, WEBP) atau PDF, maksimal 2 MB, ditambah nama bank/e-money dan "
     "nomor referensi transaksinya. Satu nomor referensi hanya bisa dipakai untuk satu pembayaran.",
     "bukti format file foto ukuran referensi transfer"),
    (P, "Apa yang terjadi setelah saya mengirim bukti pembayaran?",
     "Bukti Anda berstatus Menunggu Verifikasi sampai kasir atau admin memeriksanya. Bila disetujui, "
     "transaksi lunas dan nota bisa dibuka; bila ditolak, alasannya tampil di halaman pembayaran.",
     "setelah kirim bukti bayar tunggu verifikasi periksa"),
    (P, "Bukti pembayaran saya ditolak, apa yang harus dilakukan?",
     "Lihat alasan penolakannya di Riwayat Bukti Pembayaran pada halaman Bayar Transfer / QRIS, lalu kirim "
     "bukti baru yang benar dari halaman yang sama.",
     "bukti tolak salah transfer"),
    (P, "Bisakah saya mengirim bukti pembayaran lagi sebelum diperiksa?",
     "Tidak. Tiap transaksi hanya boleh punya satu bukti yang menunggu verifikasi. Tunggu sampai bukti itu "
     "diperiksa; bila ditolak, Anda bisa mengirim bukti baru.",
     "kirim bukti lagi dua satu"),
    (P, "Bagaimana cara membayar Home Service?",
     "Bayar tunai ke mekanik yang datang, lalu mekanik mencatatnya. Bisa juga transfer atau QRIS dari "
     "detail servis di Riwayat Servis seperti servis di bengkel.",
     "bayar tunai mekanik home service"),
    (P, "Bagaimana cara melihat nota pembayaran?",
     "Buka menu Riwayat Servis, pilih servis yang sudah dibayar, lalu klik Lihat Nota Pembayaran. Nota "
     "muncul setelah pembayaran tunai dicatat, atau setelah bukti transfer/QRIS disetujui.",
     "nota lihat cetak print bayar"),

    # ---- Biaya dan Sparepart ----
    (B, "Bagaimana biaya servis dihitung?",
     "Biaya dihitung dari layanan (jasa) dan sparepart yang dicatat mekanik selama pengerjaan. Rinciannya "
     "tertera di detail servis.",
     "biaya hitung harga layanan jasa sparepart rincian mahal"),
    (B, "Kapan saya tahu total biaya servis?",
     "Rincian dan total biaya sudah terlihat saat Anda diminta menyetujui diagnosis. Total akhir tertera di "
     "detail servis dan di nota.",
     "kapan total biaya tahu"),
    (B, "Apakah biaya bisa bertambah setelah diagnosis disetujui?",
     "Bisa, bila mekanik menambahkan layanan atau sparepart selama pengerjaan. Semua tambahan tercatat di "
     "rincian biaya pada detail servis.",
     "biaya tambah setelah setuju diagnosis naik"),
    (B, "Di mana saya bisa melihat daftar harga layanan?",
     "Bagian Daftar Harga di halaman depan menampilkan harga jasa dan perkiraan waktu tiap layanan.",
     "daftar_harga harga layanan jasa"),
    (B, "Apakah harga layanan sudah termasuk sparepart?",
     "Belum. Harga di Daftar Harga hanya untuk jasa. Sparepart dihitung terpisah sesuai yang dipakai, dan "
     "tercantum di rincian biaya yang Anda setujui lewat diagnosis.",
     "harga termasuk sparepart jasa"),

    # ---- Akun ----
    (A, "Bagaimana cara mendaftar akun?",
     "Klik Sign Up di halaman depan, isi nama lengkap, e-mail, nomor telepon (boleh dikosongkan), dan "
     "kata sandi, lalu klik Buat akun. Setelah itu Anda bisa login dengan e-mail dan kata sandi tersebut.",
     "daftar akun buat baru"),
    (A, "Saya tidak bisa login, apa yang harus dilakukan?",
     "Pastikan e-mail dan kata sandi yang diketik benar. Kalau lupa kata sandi, pakai Lupa kata sandi? di "
     "halaman login. Kalau masih tidak bisa, hubungi bengkel di {telepon_bengkel}.",
     "login gagal salah"),
    (A, "Bisakah daftar atau login dengan akun Google atau Facebook?",
     "Tidak. Pendaftaran dan login hanya memakai e-mail dan kata sandi.",
     "google facebook apple gmail sosial login daftar"),
    (A, "Saya lupa kata sandi, bagaimana cara mengatasinya?",
     "Di halaman login, klik Lupa kata sandi? lalu ikuti petunjuknya. Kalau cara itu tidak tersedia, "
     "hubungi bengkel agar admin membantu mengganti kata sandi Anda.",
     "lupa sandi reset"),
    (A, "Bagaimana cara mengganti kata sandi?",
     "Setelah login, buka menu Profil Saya. Di bagian ganti kata sandi, isi kata sandi lama dan kata sandi "
     "baru, lalu simpan. Anda tetap login setelah menggantinya.",
     "ubah sandi baru"),
    (A, "Bagaimana cara mengubah data profil dan foto?",
     "Setelah login, buka menu Profil Saya, ubah nama, e-mail, nomor telepon, alamat, atau foto profil, "
     "lalu simpan.",
     "profil ubah nama email nomor telepon alamat foto data"),

    # ---- Info Bengkel ----
    (I, "Di mana alamat bengkel?",
     "Alamat bengkel: {alamat_bengkel}.",
     "alamat lokasi bengkel letak"),
    (I, "Jam berapa bengkel buka?",
     "Jam buka bengkel: {jam_buka}.",
     "jam buka tutup operasional hari minggu sabtu"),
    (I, "Bagaimana cara menghubungi bengkel?",
     "Telepon atau WhatsApp {telepon_bengkel}, atau e-mail ke {email_bengkel}.",
     "kontak hubungi whatsapp telepon email bengkel"),
    (I, "Daerah mana saja yang dilayani Home Service?",
     "Mekanik datang ke alamat yang Anda tulis saat memesan Home Service. Untuk memastikan lokasi Anda "
     "terjangkau, hubungi bengkel di {telepon_bengkel} sebelum memesan.",
     "lokasi layan home service jauh jangkau"),
]

# Teks isi awal versi sebelumnya: baris yang jawabannya masih persis salah satu
# teks ini belum diubah admin, jadi boleh diperbarui ke FAQ_AWAL.
VERSI_LAMA = [
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
    (K, "Bagaimana cara mengubah data kendaraan?",
     "Buka menu Kendaraan Saya, pilih kendaraannya, lalu klik ubah. Data seperti nomor polisi, merek, "
     "model, dan tahun bisa diperbaiki di sana.",
     "ubah edit data kendaraan nopol salah merek model tahun"),
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

# Pertanyaan lama yang kalimatnya diganti: lama -> baru.
GANTI_PERTANYAAN = {
    "Berapa biaya servis dan kapan saya membayar?": "Bagaimana biaya servis dihitung?",
    "Bagaimana cara mengubah data profil dan nomor telepon?": "Bagaimana cara mengubah data profil dan foto?",
}


def isi_faq_awal():
    """Tambahkan FAQ awal yang belum ada; kembalikan jumlah yang dibuat. Aman diulang.

    Baris lama diperbarui hanya kalau jawabannya masih teks lama (suntingan admin tidak ditimpa).
    """
    jawaban_lama = {}
    for _, pertanyaan, jawaban, _ in VERSI_LAMA:
        baru = GANTI_PERTANYAAN.get(pertanyaan, pertanyaan)
        jawaban_lama.setdefault(baru, set()).add(jawaban)
    nama_lama = {}
    for lama, baru in GANTI_PERTANYAAN.items():
        nama_lama.setdefault(baru, []).append(lama)

    dibuat = 0
    for urutan, (kategori, pertanyaan, jawaban, kata_kunci) in enumerate(FAQ_AWAL, start=1):
        calon = [pertanyaan] + nama_lama.get(pertanyaan, [])
        ada = F.objects.filter(pertanyaan__in=calon).order_by("pk").first()
        if ada is None:
            F.objects.create(kategori=kategori, pertanyaan=pertanyaan, jawaban=jawaban,
                             kata_kunci=kata_kunci, urutan=urutan)
            dibuat += 1
        elif ada.jawaban in jawaban_lama.get(pertanyaan, ()):
            baru = {"kategori": kategori, "pertanyaan": pertanyaan, "jawaban": jawaban,
                    "kata_kunci": kata_kunci, "urutan": urutan}
            if any(getattr(ada, k) != v for k, v in baru.items()):
                for k, v in baru.items():
                    setattr(ada, k, v)
                ada.save(update_fields=list(baru))
    return dibuat
