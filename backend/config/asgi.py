"""ASGI 入口：``uvicorn config.asgi:application``。"""
import os

from django.core.asgi import get_asgi_application

from config.settings import DJANGO_ENV

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings_prod" if DJANGO_ENV in {"prod", "production"} else "config.settings_dev",
)

application = get_asgi_application()
