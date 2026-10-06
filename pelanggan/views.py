from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard_pelanggan(request):
    return render(request, "pelanggan/dashboard.html", {"user": request.user})
# Create your views here.
