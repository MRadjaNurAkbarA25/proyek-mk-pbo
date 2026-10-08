from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import RegisterForm, LoginForm
from .models import Pelanggan, User

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
            Pelanggan.objects.create(
                user=user,
                no_telepon=form.cleaned_data.get("no_telepon", ""),
                alamat=form.cleaned_data.get("alamat", ""),
            )
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