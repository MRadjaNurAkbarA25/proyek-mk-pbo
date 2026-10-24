from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('pelanggan/', include('pelanggan.urls')),
    path('kasir/', include('kasir.urls')),
    path('mekanik/', include('mekanik.urls')),
    path('adminpanel/', include('adminpanel.urls')),
    path('sparepart/', include('sparepart.urls')),
    path('pembelian/', include('pembelian.urls')),
    path('pembayaran/', include('pembayaran.urls')),
    path('', include('landing.urls')),
]

# Foto profil dilayani Django sendiri, termasuk saat DEBUG mati.
# Di server, aplikasi berjalan di gunicorn dan Nginx milik admin hosting
# hanya meneruskan permintaan ke sini; tidak ada Nginx di dalam kontainer
# yang bisa melayani folder media. Dokumentasi Django menyebut cara ini
# kurang efisien untuk situs besar, tapi cukup untuk skala bengkel ini dan
# tidak menuntut perubahan apa pun di server. Kalau nanti Nginx bisa
# membaca volume data, arahkan /media/ ke DJANGO_DATA_DIR/media di sana.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
