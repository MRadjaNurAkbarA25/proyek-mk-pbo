"""Titik masuk WSGI; variabel `application` dipakai gunicorn."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bengkel_project.settings')

application = get_wsgi_application()
