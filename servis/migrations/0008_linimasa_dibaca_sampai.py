from django.db import migrations, models
from django.db.models import Max
from django.utils import timezone


def waktu_ke_pk(apps, schema_editor):
    """Waktu baca lama -> pk baris terakhir yang sudah ada saat itu.

    Baris yang lahir pada tick jam yang sama dengan waktu baca dianggap sudah
    dibaca: sama dengan perilaku lama (`waktu > dibaca`), jadi tidak ada angka
    kabar yang tiba-tiba menyala setelah migrasi.
    """
    TransaksiServis = apps.get_model("servis", "TransaksiServis")
    PembaruanServis = apps.get_model("servis", "PembaruanServis")
    for t in TransaksiServis.objects.exclude(linimasa_dibaca_pelanggan=None):
        t.linimasa_dibaca_sampai = PembaruanServis.objects.filter(
            transaksi=t, waktu__lte=t.linimasa_dibaca_pelanggan
        ).aggregate(m=Max("pk"))["m"] or 0
        t.save(update_fields=["linimasa_dibaca_sampai"])


def pk_ke_waktu(apps, schema_editor):
    TransaksiServis = apps.get_model("servis", "TransaksiServis")
    PembaruanServis = apps.get_model("servis", "PembaruanServis")
    for t in TransaksiServis.objects.exclude(linimasa_dibaca_sampai=None):
        baris = PembaruanServis.objects.filter(pk=t.linimasa_dibaca_sampai).first()
        t.linimasa_dibaca_pelanggan = baris.waktu if baris else timezone.now()
        t.save(update_fields=["linimasa_dibaca_pelanggan"])


class Migration(migrations.Migration):

    dependencies = [
        ("servis", "0007_kendaraan_protect"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaksiservis",
            name="linimasa_dibaca_sampai",
            field=models.BigIntegerField(
                blank=True,
                editable=False,
                null=True,
                verbose_name="Linimasa terakhir dibaca pelanggan (pk baris)",
            ),
        ),
        migrations.RunPython(waktu_ke_pk, pk_ke_waktu),
        migrations.RemoveField(
            model_name="transaksiservis",
            name="linimasa_dibaca_pelanggan",
        ),
    ]
