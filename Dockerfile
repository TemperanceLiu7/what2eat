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

# 先只拷依赖清单，改代码时不必重装依赖（利用镜像层缓存）。
# 注意：requirements-cloud.txt 里用 `-r requirements.txt` 相对引用基础清单，
# 两份必须放在同一目录且保持原名；若把 cloud 清单改名为 requirements.txt，
# pip 会判定为「递归引用自身」直接报错。
COPY backend/requirements.txt /tmp/req/requirements.txt
COPY backend/requirements-cloud.txt /tmp/req/requirements-cloud.txt
RUN pip install --no-cache-dir -r /tmp/req/requirements-cloud.txt \
    && rm -rf /tmp/req

COPY backend/ /app/
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 收集 admin 的 CSS/JS。
# settings_prod 用的是 WhiteNoise 的 manifest 存储，必须用 prod 配置跑一遍才会生成 manifest；
# 这一步不连数据库，DATABASE_URL 只是为了让 settings_prod 的启动校验通过。
# 注意主机名不能写 127.0.0.1：settings_prod 会把「本机地址」判成变量没生效并直接报错。
RUN SECRET_KEY=build-only-not-used-at-runtime \
    ALLOWED_HOSTS=.up.railway.app \
    CORS_ALLOWED_ORIGINS=https://example.com \
    CSRF_TRUSTED_ORIGINS=https://example.com \
    DB_ENGINE=postgres \
    DATABASE_URL=postgresql://build:build@db.invalid:5432/build \
    python manage.py collectstatic --no-input

EXPOSE 8000

# 启动链：先起 gunicorn（端口先开），再 migrate、bootstrap，最后常驻等待。
# 逻辑写在 docker-entrypoint.sh 里并用 ENTRYPOINT 调用，而不是 CMD：
# 平台如果设过「自定义启动命令」，CMD 会被整个替换掉，ENTRYPOINT 不会，
# 之前「migrate 跑完就再没有任何日志」就是这条启动链被顶掉了。
ENTRYPOINT ["/entrypoint.sh"]
