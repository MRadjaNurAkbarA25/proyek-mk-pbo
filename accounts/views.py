from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import KeahlianForm, LoginForm, ProfilForm, RegisterForm
from .models import Mekanik, Pelanggan, User

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.no_telepon = form.cleaned_data.get("no_telepon", "").strip()
            user.save(update_fields=["no_telepon"])
            Pelanggan.objects.create(user=user)
            login(request, user)
            messages.success(request, "Registrasi berhasil. Selamat datang!")
            return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not request.POST.get("remember"):
                request.session.set_expiry(0)
            return redirect("dashboard")
        else:
            messages.error(request, "Username atau password salah.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Anda telah logout.")
    return redirect("login")


@login_required
def dashboard_view(request):
    redirect_map = {
        User.ROLE_ADMIN: "admin_dashboard",
        User.ROLE_KASIR: "kasir_dashboard",
        User.ROLE_MEKANIK: "mekanik_dashboard",
        User.ROLE_PELANGGAN: "pelanggan_dashboard",
    }
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    url_name = redirect_map.get(request.user.role)
    if url_name is None:
        # Role kosong/tidak dikenal: keluarkan user supaya tidak terjadi redirect loop
        messages.error(request, "Akun Anda belum memiliki role. Hubungi Admin.")
        logout(request)
        return redirect("login")
    return redirect(url_name)

# Peta kerangka halaman per role. Halaman Profil Saya memakai satu template,
# tetapi menumpang sidebar/navbar milik role yang sedang login.
BASE_PER_ROLE = {
    User.ROLE_PELANGGAN: "pelanggan/base.html",
    User.ROLE_MEKANIK: "mekanik/base.html",
    User.ROLE_ADMIN: "adminpanel/base.html",
    User.ROLE_KASIR: "kasir/base.html",
}


@login_required
def profil_saya(request):
    """
    Satu halaman profil untuk keempat role (lihat BASE_PER_ROLE).
    Isinya bertingkat: data pribadi dan ganti kata sandi untuk semua,
    alamat hanya untuk pelanggan dan mekanik, keahlian hanya untuk mekanik.
    """
    user = request.user
    mekanik = Mekanik.objects.filter(user=user).first()

    form = ProfilForm(instance=user)
    form_keahlian = KeahlianForm(instance=mekanik) if mekanik else None
    form_sandi = PasswordChangeForm(user)

    if request.method == "POST":
        aksi = request.POST.get("aksi", "profil")

        if aksi == "sandi":
            form_sandi = PasswordChangeForm(user, request.POST)
            if form_sandi.is_valid():
                form_sandi.save()
                # Tanpa ini pengguna langsung ter-logout setelah ganti sandi.
                update_session_auth_hash(request, form_sandi.user)
                return redirect(f"{reverse('profil_saya')}?sandi=ok")
        else:
            form = ProfilForm(request.POST, request.FILES, instance=user)
            if mekanik:
                form_keahlian = KeahlianForm(request.POST, instance=mekanik)
            valid = form.is_valid()
            if mekanik:
                valid = form_keahlian.is_valid() and valid
            if valid:
                form.save()
                if mekanik:
                    form_keahlian.save()
                return redirect(f"{reverse('profil_saya')}?simpan=ok")

    return render(request, "accounts/profil.html", {
        "base_template": BASE_PER_ROLE.get(user.role, "base.html"),
        "nav": "profil_saya",
        "form": form,
        "form_keahlian": form_keahlian,
        "form_sandi": form_sandi,
        "mekanik": mekanik,
        "jumlah_servis": mekanik.jumlah_servis if mekanik else None,
    })
