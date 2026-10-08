from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('pelanggan/', include('pelanggan.urls')),
    path('kasir/', include('kasir.urls')),
    path('mekanik/', include('mekanik.urls')),
    path('adminpanel/', include('adminpanel.urls')),
    path('sparepart/', include('sparepart.urls')),
    path('', include('landing.urls')),
]