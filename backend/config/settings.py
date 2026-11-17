"""项目基础配置（dev / prod 共用的部分）。

dev / prod 的差异在 ``config/settings_dev.py`` 与 ``config/settings_prod.py``，
两者都 ``from .settings import *``。切换开关是环境变量 ``DJANGO_ENV``（dev|prod），
由 ``manage.py`` / ``wsgi.py`` / ``asgi.py`` 读取。

约束：密钥、数据库、调试开关、跨域白名单、上传限制全部走环境变量，
本地开发用同目录的 ``.env``（参考 ``.env.example``）。
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 极简 .env 解析：不引入 python-dotenv，少一个硬依赖
# ---------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    """读取 ``KEY=VALUE`` 形式的 .env。

    - 忽略空行与 ``#`` 注释，值两端成对引号会被去掉
    - **不覆盖**已经存在的真实环境变量（生产环境变量优先级最高）
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# 环境变量读取工具
# ---------------------------------------------------------------------------
def env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    return default if value is None or value == "" else value


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        raise ImproperlyConfigured(f"环境变量 {key} 必须是整数，当前值：{raw!r}")


def env_list(key: str, default: tuple[str, ...] = ()) -> list[str]:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


DJANGO_ENV = (env("DJANGO_ENV", "dev") or "dev").strip().lower()
IS_PROD = DJANGO_ENV in {"prod", "production"}

# ---------------------------------------------------------------------------
# 安全
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", "")
if not SECRET_KEY:
    if IS_PROD:
        raise ImproperlyConfigured(
            "生产环境必须通过环境变量 SECRET_KEY 提供密钥（不要使用仓库里的默认值）"
        )
    SECRET_KEY = "dev-only-insecure-secret-key-please-change-me"

DEBUG = env_bool("DEBUG", default=not IS_PROD)

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS", ("127.0.0.1", "localhost") if not IS_PROD else ()
)
if IS_PROD and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("生产环境必须通过 ALLOWED_HOSTS 指定允许访问的域名")

# 前端（Vite dev server / 线上域名）跨域白名单，逗号分隔
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ("http://127.0.0.1:5173", "http://localhost:5173") if not IS_PROD else (),
)
# 仅开发环境默认放开；生产必须显式配置白名单
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", default=not IS_PROD)
CORS_ALLOW_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
CORS_ALLOW_HEADERS = "Authorization,Content-Type,Accept,X-Requested-With,X-CSRFToken"

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", CORS_ALLOWED_ORIGINS)

# ---------------------------------------------------------------------------
# 应用
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 第三方
    "rest_framework",
    "drf_spectacular",
    # 本项目（唯一的业务 app，9 张表都在里面）
    "core",
]

MIDDLEWARE = [
    "config.middleware.CorsMiddleware",  # 自带的最小 CORS 实现，不依赖 django-cors-headers
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# 数据库：DB_ENGINE=mysql 走 MySQL 8，否则本地 SQLite
# ---------------------------------------------------------------------------
DB_ENGINE = (env("DB_ENGINE", "sqlite") or "sqlite").strip().lower()

if DB_ENGINE in {"mysql", "mysql8", "mariadb"}:
    # Windows 上装 mysqlclient 需要编译工具链，这里退一步用纯 Python 的 PyMySQL。
    # Django 只认 MySQLdb 这个名字，垫片就是把 PyMySQL 注册成 MySQLdb。
    # 如果环境里已经有真正的 mysqlclient，就不做替换。
    try:  # noqa: SIM105
        import MySQLdb  # noqa: F401
    except ImportError:
        try:
            import pymysql

            pymysql.install_as_MySQLdb()
        except ImportError:  # pragma: no cover
            raise ImproperlyConfigured(
                "DB_ENGINE=mysql 需要 MySQL 驱动，装一个即可：pip install pymysql"
                "（或 pip install mysqlclient，需要有编译环境）"
            )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NAME", "what2eat"),
            "USER": env("DB_USER", "root"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PORT", "3306"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"},
        }
    }
elif DB_ENGINE in {"postgres", "postgresql", "pgsql"}:
    # 托管数据库通常直接给一个 DATABASE_URL，优先用它
    from urllib.parse import unquote, urlparse

    def _pg_options(host: str, default_sslmode: str) -> dict:
        """psycopg 连接参数。

        开了连接池时主机名可能带 ``-pooler``（PgBouncer 事务模式），
        这种连接不保证会话级状态，psycopg 的「会话内预编译语句」会失效，
        必须把 ``prepare_threshold`` 置空。带不带 pooler 都能跑。
        """
        # 同一项目内的内网库（Railway ``*.railway.internal``、Render ``*.internal``）
        # 一律不开 SSL：它们的 Postgres 没有配证书，默认的 require 会直接连不上。
        if (host or "").endswith(".internal") and default_sslmode == "require":
            default_sslmode = "prefer"

        options: dict = {"sslmode": env("DB_SSLMODE", default_sslmode)}
        if "-pooler" in (host or ""):
            options["prepare_threshold"] = None
        return options

    db_url = env("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        _host = parsed.hostname or ""
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": unquote((parsed.path or "").lstrip("/")),
                "USER": unquote(parsed.username or ""),
                "PASSWORD": unquote(parsed.password or ""),
                "HOST": _host,
                "PORT": str(parsed.port or 5432),
                "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
                # 托管库通常要求 SSL；同机/内网库可设 DB_SSLMODE=prefer
                "OPTIONS": _pg_options(_host, "require"),
            }
        }
    else:
        _host = env("DB_HOST", "127.0.0.1") or "127.0.0.1"
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": env("DB_NAME", "what2eat"),
                "USER": env("DB_USER", "postgres"),
                "PASSWORD": env("DB_PASSWORD", ""),
                "HOST": _host,
                "PORT": env("DB_PORT", "5432"),
                "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
                "OPTIONS": _pg_options(_host, "prefer"),
            }
        }
elif DB_ENGINE in {"sqlite", "sqlite3", ""}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": env("DB_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
            "OPTIONS": {"timeout": 20},
        }
    }
else:
    raise ImproperlyConfigured(
        f"不支持的 DB_ENGINE={DB_ENGINE!r}，可选 sqlite / mysql"
    )

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# 自定义用户表
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": env_int("PASSWORD_MIN_LENGTH", 8)}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# 国际化 / 时区
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = env("TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# 静态文件 / 媒体文件（图片先落本地 MEDIA_ROOT，生产可换对象存储）
# ---------------------------------------------------------------------------
STATIC_URL = env("STATIC_URL", "/static/")
STATIC_ROOT = Path(env("STATIC_ROOT", str(BASE_DIR / "staticfiles")))

MEDIA_URL = env("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 8 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)
# 打卡图片走 base64 直传，上限单独控制（默认 5MB）
IMAGE_MAX_BYTES = env_int("IMAGE_MAX_BYTES", 5 * 1024 * 1024)

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.EnvelopePagination",
    "PAGE_SIZE": env_int("API_PAGE_SIZE", 10),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # 统一信封：所有异常都变成 {ok:false, code, message}
    "EXCEPTION_HANDLER": "core.responses.exception_handler",
    "COERCE_DECIMAL_TO_STRING": False,
    "DATETIME_FORMAT": "iso-8601",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 120)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 7)),
    "ROTATE_REFRESH_TOKENS": env_bool("JWT_ROTATE_REFRESH", default=False),
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
}

# ---------------------------------------------------------------------------
# 接口文档
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "今天吃什么 · 校园随机推荐 API",
    "DESCRIPTION": (
        "校园「今天吃什么」后端接口。\n\n"
        "统一返回：成功 `{ok:true, data:{...}, message:\"\"}`；"
        "失败 `{ok:false, code:\"XXX\", message:\"中文提示\"}`。\n\n"
        "认证：`Authorization: Bearer <access>`。"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "SCHEMA_PATH_PREFIX": "/api",
}

# ---------------------------------------------------------------------------
# 业务参数（都可被环境变量覆盖，方便演示 / 调参）
# ---------------------------------------------------------------------------
# 随机推荐：权重 = BASE + 热度 * HEAT；排除用户最近 N 条打卡里的菜品
RECOMMEND_RECENT_LIMIT = env_int("RECOMMEND_RECENT_LIMIT", 4)
RECOMMEND_WEIGHT_BASE = float(env("RECOMMEND_WEIGHT_BASE", "1.0"))
RECOMMEND_WEIGHT_HEAT = float(env("RECOMMEND_WEIGHT_HEAT", "0.06"))

# 投票：默认时长（小时）、目标人数区间
VOTE_DEFAULT_HOURS = env_int("VOTE_DEFAULT_HOURS", 12)
VOTE_TARGET_COUNT_MIN = env_int("VOTE_TARGET_COUNT_MIN", 2)
VOTE_TARGET_COUNT_MAX = env_int("VOTE_TARGET_COUNT_MAX", 99)

# 举报：累计多少次自动禁言，禁言时长（小时）
AUTO_MUTE_REPORT_COUNT = env_int("AUTO_MUTE_REPORT_COUNT", 5)
AUTO_MUTE_HOURS = env_int("AUTO_MUTE_HOURS", 24)

# ---------------------------------------------------------------------------
# 图片识别（「今天吃了啥」自动识别菜品）
# 走 OpenAI 兼容的 chat/completions 接口；不配 LLM_API_KEY 就自动降级成手动选菜
# ---------------------------------------------------------------------------
LLM_API_KEY = env("LLM_API_KEY", "") or ""
LLM_BASE_URL = env("LLM_BASE_URL", "https://api.deepseek.com/v1") or ""
LLM_MODEL = env("LLM_MODEL", "deepseek-chat") or ""
LLM_TEMPERATURE = float(env("LLM_TEMPERATURE", "0.3"))
LLM_TIMEOUT = env_int("LLM_TIMEOUT", 30)
# 后台「禁言」批量操作默认天数
MUTE_DEFAULT_DAYS = env_int("MUTE_DEFAULT_DAYS", 3)

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
