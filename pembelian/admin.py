from django.contrib import admin, messages
from django.db.models import Count, Q

from .models import DetailPembelian, PembelianSparepart, Supplier

SELESAI = PembelianSparepart.STATUS_SELESAI
DRAF = PembelianSparepart.STATUS_DRAF


def _terkunci(obj):
    """True bila pembelian sudah SELESAI: semua pintu admin ditutup agar stok tidak dobel atau yatim.

    Stok bertambah sekali di `PembelianSparepart.selesaikan()`.
    """
    return obj is not None and obj.status == SELESAI


# --------------------------------------------------------------------- aksi massal
# `delete_selected` bawaan membatalkan seluruh pilihan (403) bila satu objek
# terkunci; aksi ini menyaring sendiri sehingga draf tetap terhapus.
@admin.action(description="Hapus draf yang dipilih")
def hapus_draf_terpilih(modeladmin, request, queryset):
    draf = list(queryset.filter(status=DRAF))
    for pembelian in draf:
        pembelian.hapus_draf()
    dilewati = queryset.count() - len(draf)
    if draf:
        modeladmin.message_user(request, f"{len(draf)} draf dihapus.", messages.SUCCESS)
    if dilewati:
        modeladmin.message_user(
            request,
            f"{dilewati} pembelian yang sudah selesai tidak dihapus.",
            messages.WARNING,
        )


@admin.action(description="Hapus baris draf yang dipilih")
def hapus_baris_draf_terpilih(modeladmin, request, queryset):
    boleh = list(queryset.filter(pembelian__status=DRAF).select_related("pembelian"))
    # Lewat `hapus_barang()` supaya `total` induk ikut dihitung ulang.
    for baris in boleh:
        baris.pembelian.hapus_barang(baris)
    dilewati = queryset.count() - len(boleh)
    if boleh:
        modeladmin.message_user(request, f"{len(boleh)} baris dihapus.", messages.SUCCESS)
    if dilewati:
        modeladmin.message_user(
            request,
            f"{dilewati} baris pada pembelian selesai tidak dihapus.",
            messages.WARNING,
        )


class TanpaHapusMassalBawaan:
    """Buang `delete_selected` bawaan (lihat catatan di atas)."""

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(Supplier)
class SupplierAdmin(TanpaHapusMassalBawaan, admin.ModelAdmin):
    list_display = ("nama", "telepon", "aktif", "jumlah_pembelian")
    list_filter = ("aktif",)
    search_fields = ("nama", "telepon")
    ordering = ("nama",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            jumlah_pembelian=Count("pembelian", distinct=True)
        )

    @admin.display(description="Jumlah Pembelian", ordering="jumlah_pembelian")
    def jumlah_pembelian(self, obj):
        return obj.jumlah_pembelian

    def has_delete_permission(self, request, obj=None):
        # FR-35: supplier tidak dihapus, hanya dinonaktifkan lewat kolom "aktif".
        # Tombol hapus dan `delete_selected` sama-sama dimatikan di sini; aturan
        # sebenarnya ada di `Supplier.delete()`.
        return False


class DetailPembelianInline(admin.TabularInline):
    model = DetailPembelian
    extra = 0
    readonly_fields = ("subtotal",)

    # `obj` di sini adalah induk (PembelianSparepart), bukan barisnya.
    def has_add_permission(self, request, obj=None):
        if _terkunci(obj):
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if _terkunci(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if _terkunci(obj):
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PembelianSparepart)
class PembelianSparepartAdmin(TanpaHapusMassalBawaan, admin.ModelAdmin):
    list_display = ("kode", "supplier", "tanggal", "metode_bayar", "status", "total")
    list_filter = ("status", "metode_bayar")
    search_fields = ("kode", "supplier__nama")
    date_hierarchy = "tanggal"
    inlines = [DetailPembelianInline]
    actions = [hapus_draf_terpilih]
    # `kode` dan `total` diisi sistem. `status` sengaja hanya-baca: satu-satunya
    # jalan ke SELESAI adalah `selesaikan()`, supaya stok ikut bertambah.
    readonly_fields = ("kode", "status", "total")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Hanya supplier aktif yang ditawarkan; supplier draf ini tetap ikut
        # supaya draf lama tidak macet setelah suppliernya dinonaktifkan.
        if "supplier" in form.base_fields:
            form.base_fields["supplier"].queryset = Supplier.objects.filter(
                Q(aktif=True) | Q(pk=getattr(obj, "supplier_id", None))
            )
        return form

    def has_change_permission(self, request, obj=None):
        # Pembelian selesai hanya bisa dilihat. Django otomatis menampilkan
        # seluruh field sebagai hanya-baca dan mengabaikan POST.
        if _terkunci(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if _terkunci(obj):
            return False
        return super().has_delete_permission(request, obj)

    def save_related(self, request, form, formsets, change):
        # Baris yang disunting lewat inline mengubah subtotal, jadi `total`
        # induk harus dihitung ulang (di view hal ini dilakukan `hitung_total`).
        super().save_related(request, form, formsets, change)
        form.instance.hitung_total()


@admin.register(DetailPembelian)
class DetailPembelianAdmin(TanpaHapusMassalBawaan, admin.ModelAdmin):
    list_display = ("pembelian", "sparepart", "jumlah", "harga_satuan", "subtotal")
    search_fields = ("pembelian__kode", "sparepart__nama")
    actions = [hapus_baris_draf_terpilih]
    # Subtotal selalu dihitung `BarisTransaksi.save()`, jadi tidak boleh diketik
    # (kalau tidak, form menolak simpan karena field wajib ini kosong).
    readonly_fields = ("subtotal",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Baris hanya boleh masuk ke draf, jadi induk selesai tidak ditawarkan.
        if db_field.name == "pembelian":
            kwargs["queryset"] = PembelianSparepart.objects.filter(status=DRAF)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        if obj is not None and _terkunci(obj.pembelian):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and _terkunci(obj.pembelian):
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.pembelian.hitung_total()

    def delete_model(self, request, obj):
        induk = obj.pembelian
        super().delete_model(request, obj)
        induk.hitung_total()
