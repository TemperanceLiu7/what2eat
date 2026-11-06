"""开发环境配置：SQLite + 宽松的安全策略，开箱即跑。

    python manage.py runserver          # DJANGO_ENV 默认就是 dev
    DJANGO_ENV=dev python manage.py migrate

想在本机连 MySQL 调试也行，只要在 .env 里写 ``DB_ENGINE=mysql`` 和账号密码。
"""
from __future__ import annotations

from .settings import *  # noqa: F401,F403
from .settings import env_bool, env_list

DEBUG = env_bool("DEBUG", default=True)

# 本机开发的 hosts：runserver / 局域网手机预览都放行
ALLOWED_HOSTS = ["*"]

# 本地开发允许任何来源跨域（Vite 5173、手机预览、curl 都行）
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])

# 演示阶段密码就随便点，别让「密码太简单」挡住注册流程
AUTH_PASSWORD_VALIDATORS = []

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# 开发时把 SQL 打出来排查 N+1 很方便：DB_LOG_SQL=1 python manage.py runserver
if env_bool("DB_LOG_SQL", default=False):
    LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
        "handlers": ["console"],
        "level": "DEBUG",
        "propagate": False,
    }
