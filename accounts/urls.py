from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("notifikasi/", views.notifikasi, name="notifikasi"),
    path("profil/", views.profil_saya, name="profil_saya"),

    # Lupa kata sandi memakai alur bawaan Django, hanya templatenya yang diganti
    # agar seragam dengan halaman Login.
    # LupaSandiView: e-mail kalau SMTP aktif, arahan ke bengkel kalau belum.
    path("lupa-sandi/", views.LupaSandiView.as_view(
        success_url=reverse_lazy("password_reset_done"),
    ), name="password_reset"),
    path("lupa-sandi/terkirim/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/lupa_sandi_terkirim.html",
    ), name="password_reset_done"),
    path("lupa-sandi/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/lupa_sandi_baru.html",
        success_url=reverse_lazy("password_reset_complete"),
    ), name="password_reset_confirm"),
    path("lupa-sandi/selesai/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/lupa_sandi_selesai.html",
    ), name="password_reset_complete"),
]