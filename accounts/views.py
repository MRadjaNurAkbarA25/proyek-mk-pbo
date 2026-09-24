from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import RegisterForm, LoginForm
from .models import Pelanggan, User


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
    role = request.user.role
    context = {"user": request.user}

    if role == User.ROLE_ADMIN:
        return render(request, "accounts/dashboard_admin.html", context)
    elif role == User.ROLE_KASIR:
        return render(request, "accounts/dashboard_kasir.html", context)
    elif role == User.ROLE_MEKANIK:
        return render(request, "accounts/dashboard_mekanik.html", context)
    elif role == User.ROLE_PELANGGAN:
        return render(request, "accounts/dashboard_pelanggan.html", context)

    return render(request, "accounts/dashboard_pelanggan.html", context)