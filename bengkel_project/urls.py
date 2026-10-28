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
    path('faq/', include('faq.urls')),
    path('', include('landing.urls')),
]

# Foto profil dilayani Django sendiri, termasuk saat DEBUG mati, karena Nginx
# milik admin hosting tidak bisa membaca volume data di kontainer.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
