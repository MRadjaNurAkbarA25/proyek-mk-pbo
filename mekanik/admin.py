from django.contrib import admin

from .models import JenisServis


@admin.register(JenisServis)
class JenisServisAdmin(admin.ModelAdmin):
    list_display = (
        "nama_servis",
        "estimasi_waktu",
        "harga",
    )

    search_fields = (
        "nama_servis",
    )

    list_filter = (
        "estimasi_waktu",
    )