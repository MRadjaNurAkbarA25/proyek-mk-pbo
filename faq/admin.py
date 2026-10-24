from django.contrib import admin

from .models import PertanyaanFAQ


@admin.register(PertanyaanFAQ)
class PertanyaanFAQAdmin(admin.ModelAdmin):
    list_display = ("pertanyaan", "kategori", "urutan", "aktif")
    list_filter = ("kategori", "aktif")
    search_fields = ("pertanyaan", "jawaban", "kata_kunci")

    def has_delete_permission(self, request, obj=None):
        # FAQ tidak dihapus, hanya dinonaktifkan (kolom "aktif").
        return False
