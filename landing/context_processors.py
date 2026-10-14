def info_bengkel(request):
    """
    Data identitas bengkel, otomatis tersedia di SEMUA template.
    Ganti isinya di sini sekali saja, semua halaman ikut berubah.
    """
    return {
        "nama_bengkel": "Nama Bengkel",
        "alamat_bengkel": "Jl. XXXX, Samarinda, Kalimantan Timur",
        "telepon_bengkel": "+62 XXXX XXXX XXXX",
        "email_bengkel": "namabengkel@gmail.com",
        "website_bengkel": "www.namabengkel.com",
        "jam_buka": [
            ("Senin - Jumat", "08.00 - 20.00"),
            ("Sabtu - Minggu", "10.00 - 16.00"),
        ],
    }
