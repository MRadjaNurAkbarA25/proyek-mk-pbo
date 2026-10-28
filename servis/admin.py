from django.contrib import admin

from sparepart.models import DetailSparepart

from .models import (
    DetailServis,
    PengajuanServis,
    TransaksiServis,
)


class _InlineBacaSaja(admin.TabularInline):
    """Detail hanya ditampilkan; penambahan lewat alur mekanik agar stok dan total konsisten."""

    extra = 0
    can_delete = False

    def has_add_permission(
        self,
        request,
        obj=None
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None
    ):
        return False


class DetailServisInline(_InlineBacaSaja):
    model = DetailServis


class DetailSparepartInline(_InlineBacaSaja):
    model = DetailSparepart


@admin.register(TransaksiServis)
class TransaksiServisAdmin(admin.ModelAdmin):

    list_display = (
        "kode_transaksi",
        "pelanggan",
        "kendaraan",
        "mekanik",
        "tipe_layanan",
        "status",
        "total_biaya",
    )

    list_filter = (
        "status",
        "tipe_layanan",
    )

    search_fields = (
        "kode_transaksi",
        "kendaraan__no_polisi",
        "pelanggan__user__username",
    )

    readonly_fields = (
        "kode_transaksi",
        "tanggal",
        "total_biaya",
    )

    inlines = [
        DetailServisInline,
        DetailSparepartInline,
    ]


@admin.register(PengajuanServis)
class PengajuanServisAdmin(admin.ModelAdmin):
    """FR-31. Keputusan terima/tolak tetap lewat halaman kasir, bukan dari sini,
    supaya aturan pada method terima()/tolak() tidak terlewat."""

    list_display = (
        "kendaraan",
        "pelanggan",
        "status",
        "tanggal_diajukan",
        "diproses_oleh",
        "transaksi",
    )
    list_filter = ("status",)
    search_fields = (
        "kendaraan__no_polisi",
        "pelanggan__user__username",
        "keluhan",
    )
    readonly_fields = ("tanggal_diajukan", "diproses_pada", "transaksi")
