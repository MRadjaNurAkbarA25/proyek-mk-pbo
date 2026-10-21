"""Penjaga struktur folder tes.

Tes setiap app tinggal di folder tests/ dengan nama test_*.py, sesuai
konvensi Django dan pytest. Dulu tersebar sebagai tests.py, tests_*.py, dan
satu test.py (tanpa "s") di akar tiap app.

Tes ini memastikan tidak ada berkas lama yang tertinggal. Itu penting
karena paket perubahan dipasang dengan mengekstrak zip, dan ekstrak tidak
pernah menghapus berkas lama.
"""
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase


def app_proyek():
    """App milik proyek: foldernya LANGSUNG di bawah folder proyek.

    Bukan sekadar "ada di dalam folder proyek": venv yang dibuat di dalam
    folder proyek (D:\\proyek-pbo\\venv) berisi app bawaan Django seperti
    admin dan messages, yang punya tests.py sendiri.
    """
    akar = Path(settings.BASE_DIR).resolve()
    for konfigurasi in apps.get_app_configs():
        folder = Path(konfigurasi.path).resolve()
        if folder.parent == akar:
            yield konfigurasi.label, folder


class StrukturTes(SimpleTestCase):
    def test_app_proyek_ditemukan(self):
        self.assertGreaterEqual(len(list(app_proyek())), 10)

    def test_tidak_ada_berkas_tes_di_akar_app(self):
        sisa = []
        for label, folder in app_proyek():
            for pola in ("tests.py", "test.py", "tests_*.py", "test_*.py"):
                sisa += [f"{label}/{f.name}" for f in folder.glob(pola)]
        self.assertEqual(sisa, [], "pindahkan ke <app>/tests/test_*.py")

    def test_folder_tests_adalah_paket(self):
        tanpa_init = [
            label for label, folder in app_proyek()
            if (folder / "tests").is_dir() and not (folder / "tests" / "__init__.py").exists()
        ]
        self.assertEqual(tanpa_init, [], "tanpa __init__.py, Django tidak menemukan tesnya")
