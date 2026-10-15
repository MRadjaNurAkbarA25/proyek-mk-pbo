from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

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

# Melayani foto profil saat DEBUG. Di server sungguhan ditangani web server.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
