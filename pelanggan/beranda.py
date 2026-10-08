"""Menyiapkan data untuk halaman Beranda pelanggan (dipanggil dari views.dashboard_pelanggan)."""
from django.utils import timezone

from kendaraan.models import Mobil, Motor, Truk
from servis.models import TransaksiServis as T

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]

TAHAP = [("Pengecekan", "check"), ("Persetujuan", "assignment"), ("Perbaikan", "build"), ("Selesai", "flag")]
INDEKS_TAHAP = {
    T.STATUS_MENUNGGU: 0,
    T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK: 0,
    T.STATUS_MENUNGGU_KONFIRMASI: 1,
    T.STATUS_DIKERJAKAN: 2,
    T.STATUS_SELESAI: 3,
}
PESAN = {
    T.STATUS_MENUNGGU: "Kendaraan Anda menunggu pemeriksaan mekanik.",
    T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK: "Menunggu mekanik menerima panggilan Home Service Anda.",
    T.STATUS_MENUNGGU_KONFIRMASI: "Mekanik telah mengirimkan rincian diagnosis dan biaya.",
    T.STATUS_DIKERJAKAN: "Kendaraan Anda sedang dalam perbaikan.",
    T.STATUS_SELESAI: "Servis selesai. Terima kasih!",
}
# warna badge: kuning / biru / hijau / merah / abu
WARNA_BADGE = {
    T.STATUS_MENUNGGU: "abu",
    T.STATUS_MENUNGGU_KONFIRMASI_MEKANIK: "kuning",
    T.STATUS_MENUNGGU_KONFIRMASI: "kuning",
    T.STATUS_DIKERJAKAN: "biru",
    T.STATUS_SELESAI: "hijau",
    T.STATUS_DIBATALKAN: "merah",
}


def _tanggal(dt):
    d = timezone.localtime(dt)
    return f"{d.day:02d} {BULAN[d.month - 1]} {d.year}"


def _label_kendaraan(k):
    return f"{k.merk} {k.model_kendaraan}" if k else "—"


def _ikon_kendaraan(k):
    tipe = k.get_tipe() if k else ""
    return {"Motor": "motor", "Truk": "truk"}.get(tipe, "mobil")


def data_beranda(user, profil):
    semua = T.objects.filter(pelanggan=profil).select_related("kendaraan", "mekanik")

    # --- kartu "Status Servis Saat Ini" ---
    aktif = semua.filter(status__in=T.STATUS_AKTIF).order_by("-tanggal").first()
    servis = None
    if aktif:
        idx = INDEKS_TAHAP.get(aktif.status, 0)
        langkah = []
        for n, (nama, ikon) in enumerate(TAHAP):
            kondisi = "selesai" if n < idx else ("sekarang" if n == idx else "belum")
            langkah.append({"nama": nama, "ikon": ikon, "kondisi": kondisi})
        k = aktif.kendaraan
        servis = {
            "kode": aktif.kode_transaksi,
            "kendaraan": f"{_label_kendaraan(k)} ({k.no_polisi})" if k else "Kendaraan belum dipilih",
            "layanan": aktif.get_tipe_layanan_display(),
            "status": aktif.get_status_display(),
            "warna": WARNA_BADGE.get(aktif.status, "abu"),
            "pesan": PESAN.get(aktif.status, ""),
            "langkah": langkah,
            "perlu_persetujuan": aktif.status == T.STATUS_MENUNGGU_KONFIRMASI,
        }

    # --- tabel "Riwayat Terakhir" (3 terbaru) ---
    riwayat = [{
        "tanggal": _tanggal(t.tanggal),
        "kendaraan": _label_kendaraan(t.kendaraan),
        "layanan": t.get_tipe_layanan_display(),
        "status": t.get_status_display(),
        "warna": WARNA_BADGE.get(t.status, "abu"),
    } for t in semua.order_by("-tanggal")[:3]]

    # --- kartu "Garasi Saya" (3 pertama) ---
    garasi = []
    for model in (Mobil, Motor, Truk):
        garasi += list(model.objects.filter(pelanggan=profil))
    garasi = [{"nama": _label_kendaraan(k), "plat": k.no_polisi, "ikon": _ikon_kendaraan(k)} for k in garasi[:3]]

    return {
        "nama": user.first_name or user.username,
        "profil_lengkap": bool(profil.alamat and profil.no_telepon),
        "servis": servis,
        "riwayat": riwayat,
        "garasi": garasi,
    }
