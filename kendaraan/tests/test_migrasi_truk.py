"""Migrasi 0002: truk yang sudah terdaftar menjadi Mobil, bukan dihapus.

Dijalankan dengan TransactionTestCase karena skema SQLite tidak boleh diubah
di dalam transaksi TestCase. Setelah selesai database dikembalikan ke migrasi
terbaru supaya uji lain tidak terganggu.
"""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


SEBELUM = [("kendaraan", "0001_initial"), ("servis", "0003_pengajuanservis"),
           ("accounts", "0002_profil_bersama")]
SESUDAH = [("kendaraan", "0002_truk_jadi_mobil"), ("servis", "0003_pengajuanservis"),
           ("accounts", "0002_profil_bersama")]


class MigrasiTrukJadiMobil(TransactionTestCase):
    def migrasi(self, target):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(target)
        return executor.loader.project_state(target).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_truk_menjadi_mobil_dengan_id_dan_relasi_yang_sama(self):
        apps = self.migrasi(SEBELUM)
        User = apps.get_model("accounts", "User")
        Pelanggan = apps.get_model("accounts", "Pelanggan")
        Truk = apps.get_model("kendaraan", "Truk")
        Pengajuan = apps.get_model("servis", "PengajuanServis")

        user = User.objects.create(username="lama", role="PELANGGAN")
        p = Pelanggan.objects.create(user=user)
        truk = Truk.objects.create(
            pelanggan=p, no_polisi="KT 3003 CC", merk="Mitsubishi", model_kendaraan="Colt Diesel",
            tahun=2018, kapasitas_muatan_kg=4000, jumlah_sumbu=2)
        pengajuan = Pengajuan.objects.create(pelanggan=p, kendaraan_id=truk.pk, keluhan="Susah starter")

        apps = self.migrasi(SESUDAH)
        Kendaraan = apps.get_model("kendaraan", "Kendaraan")
        Mobil = apps.get_model("kendaraan", "Mobil")
        Pengajuan = apps.get_model("servis", "PengajuanServis")

        mobil = Mobil.objects.get(pk=truk.pk)
        self.assertEqual(mobil.no_polisi, "KT 3003 CC")
        self.assertEqual((mobil.merk, mobil.model_kendaraan, mobil.tahun),
                         ("Mitsubishi", "Colt Diesel", 2018))
        self.assertEqual(mobil.jenis_mobil, "Truk 4000 kg")
        self.assertEqual(mobil.pelanggan_id, p.pk)
        self.assertEqual(Kendaraan.objects.count(), 1)
        self.assertEqual(Pengajuan.objects.get(pk=pengajuan.pk).kendaraan_id, truk.pk)
        with self.assertRaises(LookupError):
            apps.get_model("kendaraan", "Truk")
