"""Titik masuk ASGI; variabel `application` dipakai server ASGI."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bengkel_project.settings')

application = get_asgi_application()
