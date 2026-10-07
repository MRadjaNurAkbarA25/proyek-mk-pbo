from django.shortcuts import render
from django.db import transaction
from django.core.exceptions import ValidationError
from sparepart.models import Sparepart, DetailSparepart

@transaction.atomic
def tambah_sparepart_ke_transaksi(transaksi, sparepart_id, jumlah):
    """
    Menambahkan sparepart ke transaksi servis, mengurangi stok otomatis (FR-22),
    serta menghitung total biaya transaksi (FR-16).
    """
    sparepart = Sparepart.objects.select_for_update().get(pk=sparepart_id)
    
    # 1. Kurangi stok sparepart (FR-22)
    sparepart.kurangi_stok(jumlah)
    
    # 2. Catat dalam DetailSparepart
    detail = DetailSparepart.objects.create(
        transaksi=transaksi,
        sparepart=sparepart,
        jumlah=jumlah,
        harga_satuan=sparepart.harga
    )
    
    # 3. Hitung ulang total biaya transaksi
    transaksi.total_biaya = (transaksi.total_biaya or 0) + detail.subtotal
    transaksi.save()
    
    return detail
