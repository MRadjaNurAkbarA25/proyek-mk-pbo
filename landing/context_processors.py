def info_bengkel(request):
    """
    Data identitas bengkel, otomatis tersedia di SEMUA template.
    Ganti isinya di sini sekali saja, semua halaman ikut berubah.

    Dipakai oleh: landing page (header, hero, about, footer) dan kerangka
    halaman pelanggan, mekanik, serta halaman login/register.
    """
    return {
        "nama_bengkel": "Bengkel Siaga",
        # Alamat Fakultas Teknik Universitas Mulawarman, bukan alamat rumah
        # siapa pun — halaman ini publik dan reponya terbuka.
        "alamat_bengkel": "Jl. Sambaliung, Sempaja Selatan, Samarinda Utara, Kalimantan Timur",
        "telepon_bengkel": "+62 895-0320-2323",
        "email_bengkel": "bengkelsiaga1278@gmail.com",
        "website_bengkel": "bengkelsiaga.pbo.web.id",
        "jam_buka": [
            ("Senin - Jumat", "08.00 - 20.00"),
            ("Sabtu - Minggu", "10.00 - 16.00"),
        ],
    }
