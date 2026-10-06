from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard_mekanik(request):
    return render(request, "mekanik/dashboard.html", {"user": request.user})
