from django.urls import path
from . import views

app_name = 'sparepart'

urlpatterns = [
    path('', views.sparepart_list, name='sparepart_list'),
    path('tambah/', views.sparepart_create, name='sparepart_create'),
    path('<int:pk>/ubah/', views.sparepart_update, name='sparepart_update'),
    path('<int:pk>/hapus/', views.sparepart_delete, name='sparepart_delete'),
    path('peringatan-stok/', views.peringatan_stok, name='peringatan_stok'),
]