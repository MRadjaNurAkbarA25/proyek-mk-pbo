"""Hierarki class Laporan — rancangan dokumen bagian 5E.

    Laporan (abstract)
    |-- LaporanServis
    |-- LaporanPendapatan
    |-- LaporanStok
    `-- LaporanMekanik

Keempat laporan admin (FR-27 sampai FR-30) dulu ditulis sebagai empat fungsi
view yang berdiri sendiri. Perhitungannya benar, tapi hierarki class yang
dijanjikan dokumen tidak ada wujudnya di kode, padahal justru itu yang dinilai
sebagai penerapan OOP.

Berkas ini memindahkan perhitungannya ke dalam class, TANPA mengubah satu pun
angka yang dihasilkan. View-nya sekarang tinggal memanggil `.konteks()`.

Empat konsep OOP yang diminta NFR-4, dan di mana letaknya di sini:

    Abstraction   Laporan adalah ABC. `ambil_data()` ditandai @abstractmethod,
                  jadi Laporan sendiri tidak bisa dibuat objeknya dan setiap
                  turunan WAJIB mengisinya.
    Inheritance   Empat turunan mewarisi penyaringan tanggal dan kerangka
                  konteks dari induknya.
    Encapsulation Cara membaca dan menerapkan rentang tanggal disembunyikan di
                  _baca_rentang() dan _saring_tanggal(). Turunan memakainya
                  tanpa tahu isinya, dan tidak ada satu pun yang menulis ulang
                  logika tanggal.
    Polymorphism  `konteks()` dipanggil dengan cara yang sama persis untuk
                  keempat laporan, tetapi hasilnya berbeda karena tiap turunan
                  mengisi `ambil_data()` dan `judul` dengan caranya sendiri.
                  Lihat juga SEMUA_LAPORAN di bagian bawah berkas.
"""
from abc import ABC, abstractmethod
from datetime import datetime, time
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from accounts.models import Mekanik
from bengkel_project.paginasi import halaman_dari
from pembayaran.models import Pembayaran
from servis.models import TransaksiServis
from sparepart.models import Sparepart

NOL = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))

#: Laporan menampilkan lebih banyak baris per halaman daripada daftar kerja
#: harian, karena dibaca untuk dicari polanya, bukan untuk ditindaklanjuti
#: satu per satu.
PER_HALAMAN_LAPORAN = 25


class Laporan(ABC):
    """Kelas dasar seluruh laporan admin.

    Cara pakai sama untuk keempat turunannya:

        konteks = LaporanPendapatan(request).konteks()

    Yang memanggil tidak perlu tahu sedang memegang laporan yang mana.
    """

    judul = "Laporan"
    #: Laporan yang tidak ada hubungannya dengan tanggal (mis. stok) mematikan
    #: ini, sehingga kolom rentang tanggal tidak ikut dikirim ke template.
    pakai_rentang_tanggal = True

    def __init__(self, request):
        self.request = request
        self.tanggal_mulai, self.tanggal_selesai = self._baca_rentang()

    # ------------------------------------------------------------ abstraksi
    @abstractmethod
    def ambil_data(self):
        """Kembalikan dict isi laporan. WAJIB diisi tiap turunan."""

    # ------------------------------------------------- dipakai semua turunan
    def konteks(self):
        """Gabungan isi laporan dan keterangan rentang tanggalnya."""
        data = dict(self.ambil_data())
        if self.pakai_rentang_tanggal:
            data.setdefault("tanggal_mulai", self.tanggal_mulai)
            data.setdefault("tanggal_selesai", self.tanggal_selesai)
        return data

    # ----------------------------------------------------------- enkapsulasi
    @staticmethod
    def _awal_hari(teks):
        """'2026-10-14' -> 14 Okt 00:00 pada zona waktu proyek, bukan naive."""
        tanggal = datetime.strptime(teks, "%Y-%m-%d").date()
        return timezone.make_aware(datetime.combine(tanggal, time.min))

    @staticmethod
    def _akhir_hari(teks):
        """'2026-10-14' -> 14 Okt 23:59:59.999999 pada zona waktu proyek."""
        tanggal = datetime.strptime(teks, "%Y-%m-%d").date()
        return timezone.make_aware(datetime.combine(tanggal, time.max))

    def _baca_rentang(self):
        return (
            self.request.GET.get("tanggal_mulai", ""),
            self.request.GET.get("tanggal_selesai", ""),
        )

    def _saring_tanggal(self, queryset):
        """Terapkan rentang tanggal. Tanggal yang tidak masuk akal diabaikan."""
        if self.tanggal_mulai:
            try:
                queryset = queryset.filter(tanggal__gte=self._awal_hari(self.tanggal_mulai))
            except ValueError:
                self.tanggal_mulai = ""
        if self.tanggal_selesai:
            try:
                queryset = queryset.filter(tanggal__lte=self._akhir_hari(self.tanggal_selesai))
            except ValueError:
                self.tanggal_selesai = ""
        return queryset

    def _transaksi_selesai(self):
        """Transaksi berstatus Selesai dalam rentang tanggal. Dipakai dua turunan."""
        return self._saring_tanggal(
            TransaksiServis.objects.filter(status=TransaksiServis.STATUS_SELESAI)
        )


class LaporanServis(Laporan):
    """FR-27 — daftar seluruh transaksi servis, bisa disaring status dan tanggal."""

    judul = "Laporan Transaksi Servis"

    def ambil_data(self):
        transaksi = self._saring_tanggal(
            TransaksiServis.objects.select_related("mekanik__user").order_by("-tanggal")
        )
        status = self.request.GET.get("status", "")
        if status:
            transaksi = transaksi.filter(status=status)

        # Memakai penolong paginasi bersama, sama seperti daftar panjang lain
        # di proyek ini. Sebelumnya halaman laporan memakai Paginator sendiri
        # dan navigasinya ditulis terpisah, jadi tampilannya beda sendiri.
        halaman = halaman_dari(self.request, transaksi, PER_HALAMAN_LAPORAN)
        return {
            "transaksi": halaman,
            "halaman": halaman,
            "jumlah_total": halaman.paginator.count,
            "status": status,
            "status_choices": TransaksiServis.STATUS_CHOICES,
        }


class LaporanPendapatan(Laporan):
    """FR-28 — nilai servis selesai, uang yang benar-benar masuk, dan piutangnya."""

    judul = "Laporan Pendapatan"

    def ambil_data(self):
        transaksi = self._transaksi_selesai()
        nilai_servis = transaksi.aggregate(total=Coalesce(Sum("total_biaya"), NOL))["total"]

        per_hari = transaksi.annotate(periode=TruncDate("tanggal")).values("periode").annotate(
            total=Sum("total_biaya"), jumlah=Count("id")).order_by("-periode")
        per_bulan = transaksi.annotate(periode=TruncMonth("tanggal")).values("periode").annotate(
            total=Sum("total_biaya"), jumlah=Count("id")).order_by("-periode")

        # Pendapatan yang benar-benar diterima diambil dari modul Pembayaran,
        # bukan dari total_biaya transaksi yang statusnya Selesai tapi belum
        # tentu sudah dibayar.
        pembayaran = Pembayaran.objects.filter(transaksi__in=transaksi)
        total_dibayar = pembayaran.aggregate(total=Coalesce(Sum("total"), NOL))["total"]
        nama_metode = dict(Pembayaran.METODE_CHOICES)
        per_metode = [
            {"metode": nama_metode.get(baris["metode"], baris["metode"]),
             "jumlah": baris["jumlah"], "total": baris["total"]}
            for baris in pembayaran.values("metode").annotate(
                total=Sum("total"), jumlah=Count("id")).order_by("-total")
        ]

        return {
            "total": nilai_servis,            # nilai seluruh servis berstatus Selesai
            "total_dibayar": total_dibayar,   # uang yang benar-benar sudah masuk
            "total_piutang": nilai_servis - total_dibayar,
            "jumlah_belum_dibayar": transaksi.filter(pembayaran__isnull=True).count(),
            "per_hari": per_hari,
            "per_bulan": per_bulan,
            "per_metode": per_metode,
        }


class LaporanStok(Laporan):
    """FR-29 — stok seluruh sparepart, bisa disaring hanya yang kritis.

    Satu-satunya laporan yang tidak memakai rentang tanggal: stok adalah
    keadaan saat ini, bukan kejadian yang punya tanggal.
    """

    judul = "Laporan Stok Sparepart"
    pakai_rentang_tanggal = False

    def ambil_data(self):
        spareparts = Sparepart.objects.order_by("nama")
        hanya_kritis = self.request.GET.get("kritis") == "1"
        if hanya_kritis:
            # Disaring di Python, bukan di query, karena status stok dihitung
            # oleh properti model (satu aturan, dipakai semua halaman).
            spareparts = [s for s in spareparts if s.is_stok_kritis]
        return {"spareparts": spareparts, "hanya_kritis": hanya_kritis}


class LaporanMekanik(Laporan):
    """FR-30 — jumlah servis selesai dan pendapatan yang dihasilkan tiap mekanik."""

    judul = "Laporan Kinerja Mekanik"

    def ambil_data(self):
        transaksi = self._transaksi_selesai()

        # Semua mekanik ikut tampil, termasuk yang belum punya servis selesai.
        selesai = Q(transaksi_servis__in=transaksi)
        kinerja = Mekanik.objects.select_related("user").annotate(
            servis_selesai=Count("transaksi_servis", filter=selesai),
            total_pendapatan=Coalesce(Sum("transaksi_servis__total_biaya", filter=selesai), NOL),
        ).order_by("-servis_selesai", "user__username")

        return {
            "kinerja": kinerja,
            "tanpa_mekanik": transaksi.filter(mekanik__isnull=True).aggregate(
                jumlah=Count("id"), total=Coalesce(Sum("total_biaya"), NOL)),
        }


#: Dipakai untuk membuktikan polimorfismenya: keempat class ini bisa
#: diperlakukan sama persis walau isinya berbeda jauh.
SEMUA_LAPORAN = (LaporanServis, LaporanPendapatan, LaporanStok, LaporanMekanik)
