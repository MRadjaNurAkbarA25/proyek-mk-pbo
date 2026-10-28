def info_bengkel(request):
    """Identitas bengkel untuk semua template; ganti di sini, semua halaman ikut berubah."""
    return {
        "nama_bengkel": "Bengkel Siaga",
        # Alamat Fakultas Teknik Universitas Mulawarman, bukan alamat rumah
        # siapa pun — halaman ini publik dan reponya terbuka.
        "alamat_bengkel": "Jl. Sambaliung, Sempaja Selatan, Samarinda Utara, Kalimantan Timur",
        "telepon_bengkel": "+62 895-0320-2323",
        "email_bengkel": "bengkelsiaga1278@gmail.com",
        "website_bengkel": "bengkelsiaga.pbo.web.id",
        # Tujuan pembayaran non-tunai. CONTOH — ganti dengan rekening asli
        # bengkel, dan ganti static/images/qris.svg dengan gambar QRIS dari
        # bank/penyedia QRIS bengkel.
        "rekening_bengkel": {
            "bank": "BRI",
            "nomor": "0000-01-000000-50-0",
            "atas_nama": "Bengkel Siaga",
        },
        "jam_buka": [
            ("Senin - Jumat", "08.00 - 20.00"),
            ("Sabtu - Minggu", "10.00 - 16.00"),
        ],
    }
