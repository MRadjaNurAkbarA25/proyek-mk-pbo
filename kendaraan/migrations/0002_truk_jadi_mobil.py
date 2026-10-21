"""Hapus jenis kendaraan Truk; truk yang sudah terdaftar dijadikan Mobil.

Dokumen rancangan hanya merancang Mobil dan Motor. Truk sempat ditambahkan
di luar dokumen, lalu diputuskan dihapus (21 Okt 2026).

Truk lama TIDAK dihapus: sebagian sudah punya riwayat servis, dan transaksi
menempel ke baris induk Kendaraan (nomor polisi, merk, model, tahun). Jadi
untuk setiap truk dibuatkan baris Mobil dengan ID yang sama, lalu baris
Truk-nya dibuang bersama tabelnya. Baris induk dan semua transaksinya
tidak tersentuh.

save_base(raw=True) menyimpan HANYA baris Mobil. save() biasa akan ikut
menulis ulang baris induk Kendaraan dengan nilai kosong.
"""

from django.db import migrations


def truk_jadi_mobil(apps, schema_editor):
    Truk = apps.get_model("kendaraan", "Truk")
    Mobil = apps.get_model("kendaraan", "Mobil")
    for truk in Truk.objects.all():
        mobil = Mobil(
            kendaraan_ptr_id=truk.kendaraan_ptr_id,
            jumlah_pintu=2,
            # max_length 30. Kapasitas muatan disimpan di sini supaya
            # keterangan lamanya tidak hilang begitu saja.
            jenis_mobil=f"Truk {truk.kapasitas_muatan_kg} kg"[:30],
        )
        mobil.save_base(raw=True)


class Migration(migrations.Migration):

    dependencies = [
        ("kendaraan", "0001_initial"),
    ]

    operations = [
        # Mundur tidak dipulihkan: setelah tabel Truk dibuang, data muatan
        # dan jumlah sumbu tidak bisa dihidupkan lagi dari baris Mobil.
        migrations.RunPython(truk_jadi_mobil, migrations.RunPython.noop),
        migrations.DeleteModel(
            name="Truk",
        ),
    ]
