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

# 免费档没有 Shell、也没有一次性任务：建表与补数据只能放在启动命令里，且必须幂等。
# migrate / bootstrap 都可重复执行，每次重启（含冷启动）跑一遍是安全的。
#
# 每一步都先 echo 再执行，失败时日志里能直接看出停在哪一步（平台只给日志，不给 Shell）：
#   [boot] ... → migrate → [boot] 1/3 → bootstrap → [boot] 2/3 → gunicorn
# 端口同时监听 $PORT(默认 8000) 和 8080：平台「目标端口」跟 PORT 不一致时，
# 健康检查会一直失败而日志里毫无报错，双监听可以把这类不一致直接绕过去。
CMD ["sh", "-c", "set -e; echo \"[boot] PORT='${PORT}' pwd=$(pwd)\"; python manage.py migrate --no-input; echo '[boot] 1/3 migrate OK'; python manage.py bootstrap; echo '[boot] 2/3 bootstrap OK'; MAIN_PORT=\"${PORT:-8000}\"; BIND=\"--bind 0.0.0.0:${MAIN_PORT}\"; if [ \"$MAIN_PORT\" != \"8080\" ]; then BIND=\"$BIND --bind 0.0.0.0:8080\"; fi; echo \"[boot] 3/3 gunicorn $BIND\"; exec gunicorn config.wsgi:application $BIND --workers 1 --threads 8 --timeout 90 --graceful-timeout 30 --capture-output --access-logfile - --error-logfile - --log-level info"]
