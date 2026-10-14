from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("servis", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaksiservis",
            name="status",
            field=models.CharField(
                choices=[
                    ("MENUNGGU", "Menunggu"),
                    ("MENUNGGU_KONFIRMASI", "Menunggu Konfirmasi"),
                    ("DIKERJAKAN", "Dikerjakan"),
                    ("SELESAI", "Selesai"),
                    ("DIBATALKAN", "Dibatalkan"),
                ], max_length=30, default="MENUNGGU"
            ),
        ),
        migrations.AddField(
            model_name="transaksiservis",
            name="mekanik",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="transaksi_servis", to="accounts.mekanik",
                verbose_name="Mekanik",
            ),
        ),
    ]
