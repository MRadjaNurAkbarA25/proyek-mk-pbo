"""
Memindahkan no_telepon dan alamat dari Pelanggan ke User.

Urutannya penting:
1. field baru ditambahkan ke User,
2. isi lama disalin dari Pelanggan ke User,
3. field lama baru dihapus dari Pelanggan.
Kalau nomor 3 dijalankan lebih dulu, data pelanggan yang sudah ada akan hilang.
"""

from django.db import migrations, models


def salin_ke_user(apps, schema_editor):
    Pelanggan = apps.get_model("accounts", "Pelanggan")
    for pelanggan in Pelanggan.objects.select_related("user"):
        user = pelanggan.user
        user.no_telepon = pelanggan.no_telepon or ""
        user.alamat = pelanggan.alamat or ""
        user.save(update_fields=["no_telepon", "alamat"])


def kembalikan_ke_pelanggan(apps, schema_editor):
    """Dipakai kalau migrasi ini di-rollback."""
    Pelanggan = apps.get_model("accounts", "Pelanggan")
    for pelanggan in Pelanggan.objects.select_related("user"):
        pelanggan.no_telepon = pelanggan.user.no_telepon or ""
        pelanggan.alamat = pelanggan.user.alamat or ""
        pelanggan.save(update_fields=["no_telepon", "alamat"])


class Migration(migrations.Migration):

    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="no_telepon",
            field=models.CharField(blank=True, max_length=20, verbose_name="Nomor WhatsApp / HP"),
        ),
        migrations.AddField(
            model_name="user",
            name="alamat",
            field=models.TextField(blank=True, verbose_name="Alamat domisili lengkap"),
        ),
        migrations.AddField(
            model_name="user",
            name="jenis_kelamin",
            field=models.CharField(
                blank=True, max_length=1,
                choices=[("L", "Laki-laki"), ("P", "Perempuan")],
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="foto",
            field=models.FileField(blank=True, null=True, upload_to="foto_profil/"),
        ),
        migrations.RunPython(salin_ke_user, kembalikan_ke_pelanggan),
        migrations.RemoveField(model_name="pelanggan", name="no_telepon"),
        migrations.RemoveField(model_name="pelanggan", name="alamat"),
    ]
