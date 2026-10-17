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
    path('pembayaran/', include('pembayaran.urls')),
    path('', include('landing.urls')),
]

# Foto profil dilayani Django sendiri, termasuk saat DEBUG mati.
# Kontainer hosting menjalankan `runserver`, jadi tidak ada Nginx di dalam
# kontainer yang bisa melayani folder media. Nginx milik admin hosting hanya
# meneruskan permintaan ke sini.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
