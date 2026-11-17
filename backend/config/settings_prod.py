"""生产环境配置：MySQL 8 + 强制 DEBUG=False + 安全响应头。

启动方式（任选其一）：

    DJANGO_ENV=prod python manage.py runserver   # 只建议本地验证
    DJANGO_ENV=prod gunicorn config.wsgi:application -b 0.0.0.0:8000
    export DJANGO_SETTINGS_MODULE=config.settings_prod && gunicorn config.wsgi

必须提供的环境变量：``SECRET_KEY``、``ALLOWED_HOSTS``、
``DB_ENGINE=mysql``、``DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT``。
"""
from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403
from .settings import env_bool, env_int, env_list

DEBUG = False

# ---------------------------------------------------------------------------
# 平台健康检查 & 平台域名
# ---------------------------------------------------------------------------
# Railway 的存活探针固定用 Host: healthcheck.railway.app 打容器，和业务域名无关；
# 白名单里只写业务域名时，健康检查会被 DisallowedHost 拦掉，日志里表现为一串
# "Invalid HTTP_HOST header"，而浏览器访问反而正常（或平台一直判定实例不健康）。
# 这里把平台相关主机名自动并入，避免每次换平台/换域名都要回去改变量。
_PLATFORM_HOSTS = [
    "healthcheck.railway.app",
    "healthcheck.railway.internal",
    "healthcheck.railway.com",
    "localhost",
    "127.0.0.1",
    "[::1]",
]

# 平台注入的域名（Railway: RAILWAY_PUBLIC_DOMAIN / RENDER_EXTERNAL_HOSTNAME 等）
for _host_var in (
    "RAILWAY_PUBLIC_DOMAIN",
    "RAILWAY_PRIVATE_DOMAIN",
    "RENDER_EXTERNAL_HOSTNAME",
    "FLY_APP_NAME",
    "HOSTNAME",
):
    _host_val = (os.environ.get(_host_var) or "").strip()
    if _host_val:
        _PLATFORM_HOSTS.append(_host_val)

# 平台域名后缀通配（Django 支持以点开头的后缀匹配任意子域名）。
# 只覆盖 PaaS 分配给本服务的域名空间，不影响自有域名的白名单约束。
_PLATFORM_HOSTS += [".up.railway.app", ".railway.app", ".onrender.com"]

ALLOWED_HOSTS = list(dict.fromkeys(list(ALLOWED_HOSTS) + _PLATFORM_HOSTS))  # noqa: F405

# 反向代理下 Django 生成绝对地址、后台登录的 CSRF 校验也要认平台域名
_extra_csrf = []
for _host in ALLOWED_HOSTS:
    if not _host.startswith(".") and "." in _host:
        _extra_csrf.append(f"https://{_host}")
_extra_csrf += ["https://*.up.railway.app", "https://*.onrender.com"]
CSRF_TRUSTED_ORIGINS = list(  # noqa: F405
    dict.fromkeys(list(CSRF_TRUSTED_ORIGINS) + _extra_csrf)  # noqa: F405
)

if not SECRET_KEY or SECRET_KEY == "dev-only-insecure-secret-key-please-change-me":  # noqa: F405
    raise ImproperlyConfigured("生产环境必须设置环境变量 SECRET_KEY")

if not env_list("ALLOWED_HOSTS", ()):
    raise ImproperlyConfigured(
        "生产环境必须设置环境变量 ALLOWED_HOSTS（业务域名，逗号分隔；"
        "平台健康检查用的主机名已由代码自动并入，无需手写）"
    )

if DATABASES["default"]["ENGINE"] not in {  # noqa: F405
    "django.db.backends.mysql",
    "django.db.backends.postgresql",
}:
    raise ImproperlyConfigured(
        "生产环境请使用 MySQL 或 PostgreSQL："
        "设置 DB_ENGINE=mysql 及 DB_* 变量，或 DB_ENGINE=postgres + DATABASE_URL"
    )

# 数据库地址不能是「本机」：平台上的变量引用写错时（服务名对不上、行尾多空格），
# 平台不会报错，只会把变量解析成空字符串，settings 于是退回 DB_HOST 默认值 127.0.0.1，
# 启动时报一串 connection refused，很难看出其实是变量没生效。这里直接拦下来。
if DATABASES["default"].get("HOST", "") in {"", "127.0.0.1", "localhost"}:  # noqa: F405
    raise ImproperlyConfigured(
        "生产环境的数据库地址是 127.0.0.1/localhost，说明容器里没拿到 DATABASE_URL。"
        "请检查平台变量：DATABASE_URL 必须是数据库服务的引用而不是手打的值"
        "（Railway：Variables → Add Reference → 选 Postgres 服务 → DATABASE_URL），"
        "或显式填完整连接串；同时确认 DB_ENGINE=postgres。"
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
