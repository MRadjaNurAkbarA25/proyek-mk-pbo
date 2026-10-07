from django.contrib import admin
from .models import Sparepart, DetailSparepart

@admin.register(Sparepart)
class SparepartAdmin(admin.ModelAdmin):
    list_display = ('kode', 'nama', 'kategori', 'harga', 'stok', 'stok_minimum', 'is_stok_kritis_status')
    list_filter = ('kategori',)
    search_fields = ('kode', 'nama')
    ordering = ('nama',)

    @admin.display(boolean=True, description='Stok Kritis?')
    def is_stok_kritis_status(self, obj):
        return obj.is_stok_kritis

@admin.register(DetailSparepart)
class DetailSparepartAdmin(admin.ModelAdmin):
    list_display = ('transaksi', 'sparepart', 'jumlah', 'harga_satuan', 'subtotal')
    search_fields = ('sparepart__nama', 'transaksi__id')