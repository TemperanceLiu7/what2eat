#!/bin/sh
# 容器启动入口。
#
# 为什么放在 ENTRYPOINT 而不是 CMD：
#   平台如果被人设过「自定义启动命令（Custom Start Command）」，Docker 会用它替换掉 CMD，
#   于是我们的 migrate/bootstrap/gunicorn 整条链根本不会执行——日志里就只剩一句 migrate 输出。
#   ENTRYPOINT 不受这个影响（除非显式 --entrypoint 覆盖），因此把启动链钉在这里。
#
# 顺序刻意是「先起 web，再迁移」：
#   迁移/补数据慢或卡住时，端口至少已经开着，健康检查能看到真实状态（503 + 原因），
#   而不是像之前那样「迁移完就没日志、永远不监听」。

set -u

MAIN_PORT="${PORT:-8000}"
BIND="--bind 0.0.0.0:${MAIN_PORT}"
if [ "$MAIN_PORT" != "8080" ]; then
    # 平台目标端口与 PORT 不一致时，健康检查会一直失败且不报错；多监听一个 8080 兜底
    BIND="$BIND --bind 0.0.0.0:8080"
fi

echo "[boot] pwd=$(pwd)"
echo "[boot] PORT='${PORT:-<未设置>}' 监听参数: ${BIND}"
echo "[boot] python: $(python -V 2>&1)"

start_web() {
    # shellcheck disable=SC2086
    gunicorn config.wsgi:application $1 \
        --workers "${WEB_CONCURRENCY:-1}" \
        --threads "${WEB_THREADS:-8}" \
        --timeout 90 \
        --graceful-timeout 30 \
        --capture-output \
        --access-logfile - \
        --error-logfile - \
        --log-level info &
    WEB_PID=$!
    sleep 2
    kill -0 "$WEB_PID" 2>/dev/null
}

echo "[boot] 1/3 启动 gunicorn（端口先开，不依赖迁移结果）"
if ! start_web "$BIND"; then
    echo "[boot] 双端口绑定失败，退回单端口 ${MAIN_PORT}"
    if ! start_web "--bind 0.0.0.0:${MAIN_PORT}"; then
        echo "[boot] gunicorn 启动失败，见上方报错"
        exit 1
    fi
fi
echo "[boot] 1/3 gunicorn 已启动 pid=${WEB_PID}"

echo "[boot] 2/3 migrate"
if python manage.py migrate --no-input; then
    echo "[boot] 2/3 migrate OK"
else
    echo "[boot] 2/3 migrate 失败：服务仍在跑，/api/health/ 会返回 503 并带上数据库原因"
fi

echo "[boot] 3/3 bootstrap"
if python manage.py bootstrap; then
    echo "[boot] 3/3 bootstrap OK"
else
    echo "[boot] 3/3 bootstrap 失败：不影响进程存活，前端只是缺演示数据"
fi

echo "[boot] 启动链结束，转为等待 gunicorn（此后的日志都是请求日志）"
wait "$WEB_PID"
