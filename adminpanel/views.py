from django.shortcuts import render
from accounts.decorators import role_required
from django.shortcuts import render


@role_required("ADMIN")
def dashboard_admin(request):
    return render(request, "adminpanel/dashboard.html", {"user": request.user})
