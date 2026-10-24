"""Filter daftar sparepart: label yang jelas dan tombol Reset."""
from django.test import TestCase

from accounts.models import User
from sparepart.forms import SparepartFilterForm


class FilterSparepart(TestCase):
    def setUp(self):
        admin = User.objects.create_user(username="adm", password="x", role=User.ROLE_ADMIN)
        self.client.force_login(admin)

    def test_label_stok_kritis_jelas(self):
        self.assertEqual(SparepartFilterForm().fields["stok_kritis"].label, "Hanya stok habis/menipis")

    def test_ada_tombol_reset_ke_daftar_tanpa_filter(self):
        r = self.client.get("/sparepart/?q=oli&stok_kritis=on")
        self.assertContains(r, 'href="/sparepart/"')
        self.assertContains(r, ">Reset</a>")
