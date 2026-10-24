# Panduan untuk Claude Code — Sistem Manajemen Bengkel Siaga

Tugas kelompok PBO (S1 Informatika Unmul). Django 6.1, Python 3.12, SQLite.
Bahasa kode, komentar, pesan commit, dan balasan: **Bahasa Indonesia**.

## Perintah

```bash
python manage.py test                 # wajib OK sebelum commit/push
python manage.py makemigrations --check --dry-run   # harus "No changes detected"
python manage.py migrate
python manage.py seed_demo            # akun demo, sandi demo12345 (hanya laptop)
python manage.py runserver
```

## Aturan kerja

- **Aturan bisnis di model, bukan di view.** Perpindahan status hanya lewat
  method model (`TransaksiServis.ambil_oleh()`, `PengajuanServis.terima()`,
  `PembelianSparepart.selesaikan()`, ...). View tipis: cek akses, panggil
  method, tangkap `ValidationError`, render.
- **Tes dulu.** Fitur atau bug baru: tulis tesnya dulu dan pastikan gagal,
  baru perbaiki. Tes di `<app>/tests/test_*.py`.
- **Penerapan PBO dinilai dosen.** Pertahankan hierarki yang ada:
  `Kendaraan` → `Mobil`/`Motor` (polimorfisme `get_tipe()`,
  `deskripsi_khusus()`, `ikon`), `Laporan(ABC)` → 5 laporan,
  `BarisTransaksi` (abstrak) → `DetailSparepart`/`DetailPembelian`.
  Jangan menulis percabangan "kalau mobil … kalau motor"; pakai method-nya.
- Jenis kendaraan hanya di `Kendaraan.SUBKELAS`; pakai `relasi_subkelas()`
  dan `model_subkelas()`, jangan daftar manual.
- Stok sparepart hanya bertambah lewat pembelian (app `pembelian`) dan
  berkurang lewat servis. Jangan menambah kolom stok ke form.
- Akun kasir/mekanik dinonaktifkan, tidak dihapus. Kendaraan yang punya
  riwayat servis tidak bisa dihapus.
- Linimasa (`PembaruanServis`) ditulis lewat `TransaksiServis.catat()`; tanda
  "sudah dibaca" memakai pk baris (`linimasa_dibaca_sampai`,
  `linimasa_dibaca_mekanik_sampai`), bukan waktu.
- Halaman per role dibatasi dekorator di `accounts/decorators.py`.

## Tampilan

- Pelanggan: `pelanggan/base.html` + `static/css/pelanggan.css` dan
  `halaman.css` (komponen `.kartu`, `.tabel`, `.tbl`, `.badge-st`).
  Halaman baru jangan memakai kelas Bootstrap.
- Mekanik: `mekanik/base.html` + `mekanik.css`. Admin/kasir: `accounts/templates/kerangka.html`.
- Warna utama `--merah` di `static/css/main.css`.

## Git

- Kerja di cabang sendiri (`radja1`), merge ke `main` lewat pull request.
- Setelah `git pull`: `pip install -r requirements.txt` lalu `python manage.py migrate`.
- Jangan commit: `db.sqlite3`, `media/`, `.env`, berkas catatan pribadi
  (PETUNJUK*, PESAN*), dan kata sandi server apa pun.
- Nama file template huruf kecil (server Linux membedakan huruf besar-kecil).
- Migrasi baru: cek dulu nomor terakhir di `main`; kalau bentrok dengan
  cabang teman, ubah nomor dan `dependencies`-nya.
