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
| **Admin** | Mengelola kasir, mekanik, pelanggan, sparepart, jenis servis, dan FAQ chat; membaca laporan transaksi, pendapatan, stok, dan kinerja mekanik |

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

### Data demo

Akun demo di laptop memakai kata sandi `demo12345` (di server: nilai
`DJANGO_SANDI_DEMO`). `python manage.py seed_demo --reset` menghapus dan
mengisi ulang transaksi serta pengajuan demo (keluhan berawalan `[DEMO]`);
data buatan web tidak disentuh.

| Akun | Yang bisa diperagakan |
|---|---|
| `admin1` | Laporan (riwayat 3 bulan, label "dari home service"), Verifikasi Pembayaran, badge stok kritis dan pembelian draf |
| `kasir1` | Pengajuan menunggu, filter "Perlu tindakan" (tagihan belum dibayar, kendaraan belum tiba), verifikasi bukti transfer |
| `kasir2` | Akun nonaktif: tidak bisa login |
| `mekanik1` | Home service di lokasi: peta, Buka di Google Maps, tombol "Pelanggan setuju di lokasi"; antrian bengkel |
| `mekanik2` | Panggilan home service baru (badge), pesan pelanggan di pekerjaan yang sedang dikerjakan |
| `mekanik3` | Status Cuti: tidak muncul di pilihan home service |
| `mekanik4` | Status Tersedia tanpa pekerjaan: bisa dipilih pelanggan di Home Service |
| `pelanggan1` | Persetujuan diagnosis, linimasa dan kabar mekanik, pengingat servis berkala, alamat + titik peta di profil |
| `pelanggan2` | Pengajuan ditolak (badge Ajukan Servis), kartu "Tagihan menunggu pembayaran" |
| `pelanggan3` | Belum punya kendaraan: keadaan kosong dan instruksi tambah kendaraan |

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

CSS dan gambar disajikan aplikasi sendiri lewat WhiteNoise.

### Langkah untuk admin server

1. Isi variabel lingkungan wajib di pengaturan server (panel hosting,
   `docker -e`, atau systemd), bukan di berkas repo:
   - `DJANGO_SECRET_KEY`: kunci baru, buat dengan
     `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`
   - `DJANGO_DEBUG=0`
   - `DJANGO_ALLOWED_HOSTS=bengkelsiaga.pbo.web.id`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://bengkelsiaga.pbo.web.id`
   - `DJANGO_HTTPS=1`
   - `DJANGO_DATA_DIR=/data`
2. Arahkan `DJANGO_DATA_DIR` ke volume yang tidak hilang saat kontainer
   dibangun ulang. Isinya:
   - `db.sqlite3`: database;
   - `media/`: foto profil (dilayani publik di `/media/`);
   - `privat/`: bukti transfer/QRIS pelanggan, hanya dibuka lewat halaman
     yang memeriksa akses. Jangan diarahkan ke Nginx atau `/media/`.
3. Pasang paket: `pip install -r requirements.txt`
4. Buat tabel: `python manage.py migrate`
5. Kumpulkan berkas statis: `python manage.py collectstatic --noinput`
6. (Opsional) Data demo. Kata sandinya wajib diberikan sendiri, karena
   `demo12345` tertulis di repo publik:
   `DJANGO_SANDI_DEMO='kata-sandi-pilihan' python manage.py seed_demo`
7. Akun admin pertama: `python manage.py createsuperuser`
8. Jalankan aplikasi:
   `gunicorn bengkel_project.wsgi --bind 0.0.0.0:8000`

Setiap update:

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# lalu restart gunicorn / kontainer
```

Pemeriksaan sebelum menyalakan: `python manage.py check --deploy` hanya boleh
menyisakan `security.W004` (HSTS) dan `security.W008` (pengalihan https).
Keduanya sengaja diserahkan ke Nginx milik admin hosting; alasannya ada di
`settings.py`.

## Struktur app

| App | Isi |
|---|---|
| `accounts` | Model `User` (empat role), `Mekanik`, `Pelanggan`; login, daftar, profil, lupa sandi; pembatasan halaman per role (`decorators.py`); template bersama |
| `kendaraan` | Hierarki `Kendaraan` → `Mobil`, `Motor` |
| `servis` | `TransaksiServis` dan alur statusnya, `DetailServis`, `PengajuanServis`, `PembaruanServis` (linimasa) |
| `sparepart` | Stok sparepart dan peringatan stok minimum |
| `pembelian` | Supplier dan pembelian sparepart (FR-35); satu-satunya jalan stok bertambah |
| `pembayaran` | `Pembayaran` dan detail per metode: `PembayaranCash`, `PembayaranTransfer`, `PembayaranEWallet` |
| `laporan` | Hierarki `Laporan` (abstrak) → `LaporanServis`, `LaporanPendapatan`, `LaporanStok`, `LaporanMekanik`, `LaporanPembelian` |
| `pelanggan`, `kasir`, `mekanik`, `adminpanel` | Halaman masing-masing role |
| `landing` | Halaman depan dan identitas bengkel |
| `faq` | FR-34: `PertanyaanFAQ` dan pencocokan kata kunci (`skor_kecocokan`, `cari`), endpoint JSON `/faq/daftar/` dan `/faq/cari/`, gelembung chat (`_gelembung.html`, `static/js/faq.js`), isi awal untuk `seed_demo`. Menu Kelola FAQ untuk admin ada di `adminpanel` |

## Konsep PBO di dalam kode

- **Inheritance dan polymorphism**: `Kendaraan` → `Mobil`/`Motor`
  dengan `get_tipe()` dan `deskripsi_khusus()` yang berbeda per kelas.
  `Laporan` (kelas abstrak) → empat jenis laporan.
- **Encapsulation**: status transaksi tidak diubah langsung, tapi lewat
  method `TransaksiServis`, misalnya `ambil_oleh()`, `input_diagnosis()`,
  `konfirmasi()`, dan `selesaikan()`, yang masing-masing memeriksa apakah
  perpindahan itu sah dan mencatatnya ke linimasa.
- **Logika di model, bukan di JavaScript**: pencocokan kata kunci FAQ chat ada di
  `PertanyaanFAQ.skor_kecocokan()` dan `PertanyaanFAQ.cari()`, sehingga bisa diuji.
  JavaScript hanya menampilkan hasilnya. Chatbot ini berbasis aturan, tanpa AI,
  dan tidak menyimpan riwayat percakapan.
- **Satu aturan, satu tempat**: misalnya aturan "satu kendaraan, satu
  pekerjaan berjalan" hanya ditulis di
  `TransaksiServis.alasan_kendaraan_tidak_bisa_dilayani()`, dan semua jalur
  pembuatan transaksi melewati `TransaksiServis.buka()`.

Kode FR-xx di komentar merujuk ke dokumen rancangan kelompok.
