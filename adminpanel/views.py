from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard_admin(request):
    return render(request, "adminpanel/dashboard.html", {"user": request.user})
