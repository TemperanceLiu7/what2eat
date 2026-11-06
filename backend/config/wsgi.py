"""WSGI 入口：``gunicorn config.wsgi:application``。"""
import os

from django.core.wsgi import get_wsgi_application

from config.settings import DJANGO_ENV

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings_prod" if DJANGO_ENV in {"prod", "production"} else "config.settings_dev",
)

application = get_wsgi_application()
