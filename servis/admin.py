from django.contrib import admin

from sparepart.models import DetailSparepart

from .models import (
    DetailServis,
    TransaksiServis,
)


class _InlineBacaSaja(admin.TabularInline):
    """
    Detail hanya ditampilkan.
    Penambahan dilakukan melalui alur mekanik
    agar stok dan total biaya tetap konsisten.
    """

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