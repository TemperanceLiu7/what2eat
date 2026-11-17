# what2eat 后端镜像
#
# 用途：Koyeb / Fly.io / 任意容器平台的统一构建入口。
# 前端（Vite）仍由 Cloudflare Pages 构建，不进这个镜像；镜像里只有 backend/。
#
# 本地自测：
#   docker build -t what2eat-api .
#   docker run -p 8000:8000 -e SECRET_KEY=x -e ALLOWED_HOSTS=.koyeb.app ... what2eat-api

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_ENV=prod

WORKDIR /app

# 先只拷依赖清单，改代码时不必重装依赖（利用镜像层缓存）
COPY backend/requirements-cloud.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/

# 收集 admin 的 CSS/JS。
# settings_prod 用的是 WhiteNoise 的 manifest 存储，必须用 prod 配置跑一遍才会生成 manifest；
# 这一步不连数据库，DATABASE_URL 只是为了让 settings_prod 的启动校验通过。
RUN SECRET_KEY=build-only-not-used-at-runtime \
    ALLOWED_HOSTS=.koyeb.app \
    CORS_ALLOWED_ORIGINS=https://example.com \
    CSRF_TRUSTED_ORIGINS=https://example.com \
    DB_ENGINE=postgres \
    DATABASE_URL=postgresql://build:build@127.0.0.1:5432/build \
    python manage.py collectstatic --no-input

EXPOSE 8000

# 免费档没有 Shell、也没有一次性任务：建表与补数据只能放在启动命令里，且必须幂等。
# migrate / bootstrap 都可重复执行，每次重启（含冷启动）跑一遍是安全的。
CMD ["sh", "-c", "python manage.py migrate --no-input && python manage.py bootstrap && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 60"]
