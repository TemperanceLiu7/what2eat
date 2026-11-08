"""生产环境配置：MySQL 8 + 强制 DEBUG=False + 安全响应头。

启动方式（任选其一）：

    DJANGO_ENV=prod python manage.py runserver   # 只建议本地验证
    DJANGO_ENV=prod gunicorn config.wsgi:application -b 0.0.0.0:8000
    export DJANGO_SETTINGS_MODULE=config.settings_prod && gunicorn config.wsgi

必须提供的环境变量：``SECRET_KEY``、``ALLOWED_HOSTS``、
``DB_ENGINE=mysql``、``DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT``。
"""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403
from .settings import env_bool, env_int, env_list

DEBUG = False

if not SECRET_KEY or SECRET_KEY == "dev-only-insecure-secret-key-please-change-me":  # noqa: F405
    raise ImproperlyConfigured("生产环境必须设置环境变量 SECRET_KEY")

if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("生产环境必须设置环境变量 ALLOWED_HOSTS")

if DATABASES["default"]["ENGINE"] not in {  # noqa: F405
    "django.db.backends.mysql",
    "django.db.backends.postgresql",
}:
    raise ImproperlyConfigured(
        "生产环境请使用 MySQL 或 PostgreSQL："
        "设置 DB_ENGINE=mysql 及 DB_* 变量，或 DB_ENGINE=postgres + DATABASE_URL"
    )

# 跨域只认白名单（不做通配）
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", ())
if not CORS_ALLOWED_ORIGINS and not CORS_ALLOW_ALL_ORIGINS:
    raise ImproperlyConfigured(
        "生产环境必须配置 CORS_ALLOWED_ORIGINS（前端域名，逗号分隔）"
    )

# 反向代理 / HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", default=True)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# 静态文件交给 Nginx / WhiteNoise，媒体文件建议换对象存储
# 没有 Nginx 时，用 WhiteNoise 直接从进程里发 static
try:
    import whitenoise  # noqa: F401

    # WhiteNoise 必须紧跟 SecurityMiddleware
    _mw = list(MIDDLEWARE)  # noqa: F405
    _wm = "whitenoise.middleware.WhiteNoiseMiddleware"
    if _wm not in _mw:
        _mw.insert(1, _wm)
    MIDDLEWARE = _mw

    _static_backend = "whitenoise.storage.CompressedManifestStaticFilesStorage"
except ImportError:  # 没装 whitenoise 时退回默认（需要 Nginx 之类托管 static）
    _static_backend = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": _static_backend},
}

# 生产不打 SQL
LOGGING["loggers"]["django.db.backends"]["level"] = "ERROR"  # noqa: F405
