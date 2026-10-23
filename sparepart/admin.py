from django.contrib import admin
from .models import Sparepart, DetailSparepart

@admin.register(Sparepart)
class SparepartAdmin(admin.ModelAdmin):
    list_display = ('kode', 'nama', 'kategori', 'harga', 'stok', 'stok_minimum', 'kondisi_stok')
    list_filter = ('kategori',)
    search_fields = ('kode', 'nama')
    ordering = ('nama',)
    # FR-35: stok hanya bergerak lewat pembelian dan servis, tidak diketik di /admin/.
    readonly_fields = ('stok',)

    @admin.display(description='Kondisi Stok')
    def kondisi_stok(self, obj):
        """Tiga tingkat, bukan centang ya/tidak, supaya stok habis bisa
        dibedakan dari stok yang sekadar menipis."""
        return obj.label_stok

@admin.register(DetailSparepart)
class DetailSparepartAdmin(admin.ModelAdmin):
    list_display = ('transaksi', 'sparepart', 'jumlah', 'harga_satuan', 'subtotal')
    search_fields = ('sparepart__nama', 'transaksi__id')