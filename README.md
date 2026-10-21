# Sistem Manajemen Bengkel Siaga

Tugas kelompok mata kuliah Pemrograman Berorientasi Objek, S1 Informatika
Universitas Mulawarman. Aplikasi web Django untuk mengelola servis kendaraan
di bengkel maupun panggilan ke rumah (home service).

Situs: <https://bengkelsiaga.pbo.web.id>

## Empat role

| Role | Yang bisa dilakukan |
|---|---|
| **Pelanggan** | Mendaftarkan kendaraan, mengajukan servis di bengkel, memesan home service, menyetujui diagnosis, melihat riwayat dan linimasa perkembangan servis, membuka nota |
| **Kasir** | Meninjau pengajuan servis, membuat transaksi, menandai kendaraan tiba, memproses pembayaran (tunai, transfer, e-wallet) |
| **Mekanik** | Mengambil pekerjaan dari antrian, menerima panggilan home service, menulis diagnosis, mencatat layanan dan sparepart, menulis kabar perkembangan |
| **Admin** | Mengelola kasir, mekanik, pelanggan, sparepart, dan jenis servis; membaca laporan transaksi, pendapatan, stok, dan kinerja mekanik |

## Menjalankan di laptop

Butuh Python 3.12 atau lebih baru.

```bash
python -m venv venv
venv\Scripts\activate            # Windows. Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo       # akun dan data contoh
python manage.py runserver
```

Akun demo di laptop memakai kata sandi `demo12345`: `admin1`, `kasir1`,
`mekanik1`, `mekanik2`, `pelanggan1`, `pelanggan2`.

**Setiap habis `git pull`**, jalankan lagi `pip install -r requirements.txt`
dan `python manage.py migrate`. Keduanya tidak mengubah apa pun kalau memang
tidak ada yang baru.

## Tes

```bash
python manage.py test
```

Tes tiap app ada di `<app>/tests/test_*.py`. Seluruh tes selesai dalam
hitungan detik.

## Deploy ke server

Daftar environment variable ada di [`.env.example`](.env.example). Yang wajib:
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_HTTPS=1`, dan `DJANGO_DATA_DIR`.

Setiap deploy:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn bengkel_project.wsgi --bind 0.0.0.0:8000
```

CSS dan gambar disajikan aplikasi sendiri lewat WhiteNoise.

Akun admin pertama: `python manage.py createsuperuser`. Untuk data demo di
server, kata sandinya wajib diberikan sendiri, karena `demo12345` tertulis di
repo publik:

```bash
DJANGO_SANDI_DEMO='kata-sandi-pilihan' python manage.py seed_demo
```

## Struktur app

| App | Isi |
|---|---|
| `accounts` | Model `User` (empat role), `Mekanik`, `Pelanggan`; login, daftar, profil, lupa sandi; pembatasan halaman per role (`decorators.py`); template bersama |
| `kendaraan` | Hierarki `Kendaraan` → `Mobil`, `Motor`, `Truk` |
| `servis` | `TransaksiServis` dan alur statusnya, `DetailServis`, `PengajuanServis`, `PembaruanServis` (linimasa) |
| `sparepart` | Stok sparepart dan peringatan stok minimum |
| `pembayaran` | `Pembayaran` dan detail per metode: `PembayaranCash`, `PembayaranTransfer`, `PembayaranEWallet` |
| `laporan` | Hierarki `Laporan` (abstrak) → `LaporanServis`, `LaporanPendapatan`, `LaporanStok`, `LaporanMekanik` |
| `pelanggan`, `kasir`, `mekanik`, `adminpanel` | Halaman masing-masing role |
| `landing` | Halaman depan dan identitas bengkel |

## Konsep PBO di dalam kode

- **Inheritance dan polymorphism**: `Kendaraan` → `Mobil`/`Motor`/`Truk`
  dengan `get_tipe()` dan `deskripsi_khusus()` yang berbeda per kelas.
  `Laporan` (kelas abstrak) → empat jenis laporan.
- **Encapsulation**: status transaksi tidak diubah langsung, tapi lewat
  method `TransaksiServis`, misalnya `ambil_oleh()`, `input_diagnosis()`,
  `konfirmasi()`, dan `selesaikan()`, yang masing-masing memeriksa apakah
  perpindahan itu sah dan mencatatnya ke linimasa.
- **Satu aturan, satu tempat**: misalnya aturan "satu kendaraan, satu
  pekerjaan berjalan" hanya ditulis di
  `TransaksiServis.alasan_kendaraan_tidak_bisa_dilayani()`, dan semua jalur
  pembuatan transaksi melewati `TransaksiServis.buka()`.

Kode FR-xx di komentar merujuk ke dokumen rancangan kelompok.
