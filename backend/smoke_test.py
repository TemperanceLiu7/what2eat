#!/usr/bin/env python
"""联调冒烟脚本：对着**已经启动**的服务跑一遍核心链路，只用标准库。

    # 终端 1
    python manage.py runserver 127.0.0.1:8000
    # 终端 2（先 seed 才有数据）
    python manage.py seed
    python smoke_test.py --base http://127.0.0.1:8000/api

和 ``manage.py test`` 的区别：这里走真实 HTTP + 真实数据库（dev SQLite），
用来验证「路由 / 中间件 / JWT / 序列化 / 真实落库」整条链路，单元测试则用隔离测试库。
任何断言失败会打印细节并以退出码 1 结束。依赖：无（urllib + json）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000/api"
TIMEOUT = 10

PASSED: list[str] = []
FAILED: list[str] = []


def call(method: str, path: str, base: str, body: dict | None = None, token: str | None = None):
    """发一个请求，返回 (status_code, payload)。4xx/5xx 也正常返回，不抛异常。"""
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8", "replace")
            return response.status, _parse(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        return exc.code, _parse(raw)
    except urllib.error.URLError as exc:
        print(f"\n连不上 {url}：{exc.reason}")
        print("请先启动服务：python manage.py runserver 127.0.0.1:8000")
        sys.exit(2)


def _parse(raw: str):
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {"_raw": raw[:200]}


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  [PASS] {name}")
    else:
        FAILED.append(f"{name} {detail}".strip())
        print(f"  [FAIL] {name}  {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="今天吃什么 · 后端联调冒烟")
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"API 前缀，默认 {DEFAULT_BASE}")
    parser.add_argument("--keep", action="store_true", help="保留本次创建的数据（默认也保留，只提示）")
    args = parser.parse_args()
    base = args.base

    suffix = str(int(time.time()))[-6:]
    username = f"smoke_{suffix}"
    # seed 里的 3 条学籍；已被别的账号绑掉的会自动跳过，保证脚本可重复跑
    roster = [
        ("20230001", "张同学", "计算机学院"),
        ("20230002", "李同学", "外国语学院"),
        ("20230003", "王同学", "机械工程学院"),
    ]

    print(f"→ 目标：{base}\n")

    # 1. 公共列表（同时验证服务活着）
    print("1) 公共接口")
    status, body = call("GET", "/dishes/?page_size=1", base)
    check("GET /dishes/ 200 + 信封", status == 200 and body.get("ok") is True, f"status={status} {body}")
    check("分页字段齐全", set(body.get("data", {})) >= {"items", "total", "page", "page_size", "pages"})

    status, body = call("GET", "/dishes/random/?source=canteen", base)
    check("GET /dishes/random/ 200", status == 200 and body.get("ok") is True, f"status={status} {body}")
    dish = (body.get("data") or {}).get("dish") or {}
    check("随机结果含 dish.id / shop", bool(dish.get("id")) and "shop" in dish, str(dish)[:200])

    # 2. 注册 + 登录
    print("\n2) 注册 / 登录")
    status, body = call(
        "POST",
        "/auth/register/",
        base,
        {"username": username, "password": "pass1234", "name": "烟测同学", "college": "计算机学院"},
    )
    check("POST /auth/register/ 201", status == 201 and body.get("ok") is True, f"status={status} {body}")
    token = (body.get("data") or {}).get("access") or ""
    check("注册返回 access token", bool(token))
    check("注册后 verified=false", (body.get("data") or {}).get("user", {}).get("verified") is False)

    status, body = call("POST", "/auth/token/", base, {"username": username, "password": "pass1234"})
    check("POST /auth/token/ 200", status == 200 and "access" in (body.get("data") or {}), f"status={status}")

    # 3. 三重核验
    print("\n3) 学号三重核验")
    status, body = call(
        "POST",
        "/auth/bind-student/",
        base,
        {"student_id": roster[0][0], "name": roster[0][1], "college": "外国语学院"},
        token,
    )
    check(
        "错误学院 → 400 INVALID_DATA",
        status == 400 and body.get("code") == "INVALID_DATA",
        f"status={status} {body}",
    )

    bound = False
    for student_id, name, college in roster:
        status, body = call(
            "POST",
            "/auth/bind-student/",
            base,
            {"student_id": student_id, "name": name, "college": college},
            token,
        )
        if status == 200 and (body.get("data") or {}).get("verified") is True:
            bound = True
            print(f"     命中可用学籍：{student_id} {name} {college}")
            break
    check("正确三重 → 200 已核验", bound, f"status={status} {body}")

    if not bound:
        print(
            "\n3 条演示学籍都已被绑定（重复跑会这样）。先执行 `python manage.py seed --reset` 再跑本脚本。"
        )
        return 1

    # 4. 打卡
    print("\n4) 打卡")
    status, body = call(
        "POST", "/checkins/", base, {"content": f"烟测打卡 {suffix}，三食堂牛肉面", "dish_id": dish.get("id")}, token
    )
    check("POST /checkins/ 201", status == 201 and body.get("ok") is True, f"status={status} {body}")
    checkin = (body.get("data") or {}).get("checkin") or {}
    check("打卡返回 id / at", bool(checkin.get("id")) and checkin.get("at", 0) > 0)

    status, body = call("GET", "/checkins/?page_size=5", base, token=token)
    check("GET /checkins/ 200", status == 200 and body.get("ok") is True, f"status={status}")

    # 5. 点赞 / 收藏
    print("\n5) 点赞 / 收藏")
    status, body = call("POST", "/likes/toggle/", base, {"target_type": "dish", "target_id": dish.get("id")}, token)
    check("点赞 → liked=true", status == 200 and (body.get("data") or {}).get("liked") is True, f"status={status} {body}")
    likes_after = (body.get("data") or {}).get("likes")
    status, body = call("POST", "/likes/toggle/", base, {"target_type": "dish", "target_id": dish.get("id")}, token)
    check(
        "再点一次 → liked=false 且计数回落",
        (body.get("data") or {}).get("liked") is False and (body.get("data") or {}).get("likes") != likes_after,
        f"status={status} {body}",
    )

    status, body = call(
        "POST", "/favorites/toggle/", base, {"target_type": "dish", "target_id": dish.get("id")}, token
    )
    check("收藏 → favorited=true", status == 200 and (body.get("data") or {}).get("favorited") is True, f"status={status}")

    status, body = call("GET", "/favorites/", base, token=token)
    items = (body.get("data") or {}).get("items") or []
    check("GET /favorites/ 含刚收藏的菜", status == 200 and any(i.get("id") == dish.get("id") for i in items), f"status={status}")

    # 6. 投票
    print("\n6) 投票")
    status, body = call(
        "POST", "/votes/", base, {"title": f"烟测投票 {suffix}", "target": "西门鸡公煲", "target_count": 3}, token
    )
    check("POST /votes/ 201", status == 201, f"status={status} {body}")
    vote = (body.get("data") or {}).get("vote") or {}
    check("need = floor(3/2)+1 = 2", vote.get("need") == 2, f"need={vote.get('need')}")
    vote_id = vote.get("id")

    status, body = call("POST", f"/votes/{vote_id}/cast/", base, {"option": "agree"}, token)
    check("投票 agree 200", status == 200 and (body.get("data") or {}).get("vote", {}).get("agree_count") == 1, f"status={status} {body}")

    status, body = call("POST", f"/votes/{vote_id}/cast/", base, {"option": "agree"}, token)
    check(
        "重复投 → 409 ALREADY_VOTED",
        status == 409 and body.get("code") == "ALREADY_VOTED",
        f"status={status} {body}",
    )

    status, body = call("GET", "/votes/", base, token=token)
    votes = (body.get("data") or {}).get("items") or []
    mine = [v for v in votes if v.get("id") == vote_id]
    check(
        "GET /votes/ 回显 my_option",
        status == 200 and bool(mine) and mine[0].get("my_option") == "agree",
        f"status={status}",
    )

    # 7. 举报参数校验（不真的举报别人）
    print("\n7) 举报 / 边界")
    status, body = call(
        "POST",
        "/reports/",
        base,
        {"reported_id": 999999, "target_type": "dish", "target_id": dish.get("id"), "reason": "烟测"},
        token,
    )
    check("举报不存在的用户 → 400 INVALID_DATA", status == 400 and body.get("code") == "INVALID_DATA", f"status={status}")

    status, body = call("GET", "/dishes/random/?source=spaceship", base)
    check("非法 source → 400 INVALID_DATA", status == 400 and body.get("code") == "INVALID_DATA", f"status={status}")

    status, body = call("GET", "/auth/register/", base)
    check("未登录访问受限接口 → 401", status in (401, 405), f"status={status}")

    # 8. 文档 / 后台 / CORS
    print("\n8) 文档 / 后台 / CORS")
    root = base.rstrip("/").rsplit("/api", 1)[0] or "http://127.0.0.1:8000"
    # Swagger UI 是 HTML，这里不能带 Accept: application/json，否则 DRF 会回 406
    for path, label in (("/api/docs/", "GET /api/docs/ 200"), ("/admin/login/", "GET /admin/login/ 200")):
        try:
            with urllib.request.urlopen(f"{root}{path}", timeout=TIMEOUT) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        check(label, status == 200, f"status={status}")
    status, _ = call("GET", "/api/schema/", root)
    check("GET /api/schema/ 200", status == 200, f"status={status}")

    request = urllib.request.Request(f"{base.rstrip('/')}/dishes/random/", method="OPTIONS")
    request.add_header("Origin", "http://localhost:5173")
    request.add_header("Access-Control-Request-Method", "GET")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            status = response.status
            allow_origin = response.headers.get("Access-Control-Allow-Origin")
    except urllib.error.HTTPError as exc:
        status, allow_origin = exc.code, exc.headers.get("Access-Control-Allow-Origin")
    check("OPTIONS 预检 204 + CORS 头", status == 204 and allow_origin == "http://localhost:5173",
          f"status={status} allow_origin={allow_origin}")

    # 汇总
    print("\n" + "=" * 60)
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        for item in FAILED:
            print(f"  ✗ {item}")
        return 1
    print("全部通过 ✅")
    print(f"本次创建的测试账号：{username}（密码 pass1234，已绑定 {student_id}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
