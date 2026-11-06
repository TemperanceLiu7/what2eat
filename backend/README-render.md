# 免费云部署：Render（后端）+ Neon（数据库）+ UptimeRobot（保活）

目标：**0 元**、**永久在线**、同学随时打开都有真数据。

```
浏览器 ──► Cloudflare Pages（前端，已部署）
              │  https 请求
              ▼
        Render 免费实例（Django + gunicorn）
              │  psycopg + ssl
              ▼
        Neon 免费 PostgreSQL
```

数据库引擎是 **PostgreSQL**。本地开发仍然是 **MySQL 8**（`DB_ENGINE=mysql`），一套代码两个引擎——答辩时本地演示 MySQL，线上演示 PostgreSQL。

---

## 0. 准备工作

- 仓库 `Ares5807/what2eat` 已推到 GitHub（含根目录的 `render.yaml`）
- 需要注册两个免费账号：<https://neon.tech> 和 <https://render.com>（都能用 GitHub 登录，不用绑卡）

---

## 1. Neon：建数据库

1. 登录 <https://console.neon.tech> → **New Project**
2. Name 填 `what2eat`，Region 选离你近的（如 Singapore）
3. 建好后进 **Dashboard → Connection string**，格式选 **URI**，并选 **Direct connection**（不要用 pooled / pgbouncer，迁移更稳）
4. 复制这串，形如：

```
postgresql://neondb_owner:AbCdEf123456@ep-cool-name-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

> 库名默认是 `neondb`，不用改；Django 直接用 URL 里的库名。
> 这串就是后面要填的 `DATABASE_URL`，**别泄露到公开仓库**。

---

## 2. Render：部署后端

### 方式 A：用 Blueprint（推荐，配置已写好）

1. 登录 <https://dashboard.render.com> → **New → Blueprint**
2. 选仓库 `Ares5807/what2eat` → Apply
3. Render 读取根目录 `render.yaml`，自动建服务 `what2eat-api`
4. 它会提示你填两个 `sync: false` 的变量：
   - `DATABASE_URL`：粘第 1 步的 Neon 连接串
   - `DEMO_ADMIN_PASSWORD`：后台账号 `admin` 的密码，自己定

### 方式 B：手动建 Web Service

| 字段 | 值 |
|---|---|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements-render.txt && python manage.py collectstatic --no-input && python manage.py migrate --no-input && python manage.py seed --admin` |
| Start Command | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60` |

环境变量（Environment）：

| Key | Value |
|---|---|
| `DJANGO_ENV` | `prod` |
| `DB_ENGINE` | `postgres` |
| `DB_SSLMODE` | `require` |
| `DATABASE_URL` | Neon 连接串 |
| `SECRET_KEY` | 随便生成 64 位随机串 |
| `ALLOWED_HOSTS` | `.onrender.com,localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | `https://what2eatt.pages.dev` |
| `DEMO_ADMIN_PASSWORD` | 自己定 |

> `RENDER_EXTERNAL_HOSTNAME` 由 Render 自动注入，`settings_prod.py` 会自动把它加进 `ALLOWED_HOSTS`，所以换域名不会 500。

---

## 3. 首次部署会发生什么

Build 阶段依次执行：装依赖 → `collectstatic`（WhiteNoise 哈希压缩）→ `migrate`（建 15 张表）→ `seed --admin`（6 档口 / 16 菜品 / 3 学籍 / admin 账号）。

日志里看到这些就说明成功：

```
Applying core.0001_initial... OK
154 static files copied ... 444 post-processed
```

验证接口（浏览器直接开）：

```
https://what2eat-api.onrender.com/api/dishes/          # 应该返回菜品列表
https://what2eat-api.onrender.com/api/docs             # Swagger 文档
https://what2eat-api.onrender.com/admin/               # 后台，admin / 你设的密码
```

---

## 4. 前端切到真接口

在**前端根目录**（`what2eat/`）新建 `.env.local`：

```
VITE_API_BASE=https://what2eat-api.onrender.com/api
VITE_USE_MOCK=false
```

然后重新构建并推送：

```bash
node node_modules/vite/bin/vite.js build   # 或 pnpm build
```

> `VITE_API_BASE` 是**构建时**注入的，改了必须重新构建 + 重推，Cloudflare Pages 会自动重建。
>
> 切之前先确认后端通了，否则线上站点会大面积报错。想随时退回演示版：把 `VITE_USE_MOCK` 删掉或改回 `true` 再推一次。

---

## 5. UptimeRobot 保活（关键）

Render 免费实例 **15 分钟没人访问就休眠**，冷启动 30~60 秒，同学第一次打开会以为挂了。

1. 注册 <https://uptimerobot.com>（免费版 50 个监控，5 分钟间隔）
2. Add New Monitor：
   - Monitor Type：`HTTP(s)`
   - Friendly Name：`what2eat api`
   - URL：`https://what2eat-api.onrender.com/api/dishes/`
   - Monitoring Interval：`5 minutes`
3. 保存

这样 24 小时都有人"敲门"，实例基本不会休眠。

---

## 6. 已知限制（写报告时可以照抄）

| 限制 | 影响 | 应对 |
|---|---|---|
| Render 免费实例休眠 | 无保活时首启 30~60 秒 | UptimeRobot 每 5 分钟 ping |
| 免费实例**无持久磁盘** | 重新部署后打卡图片（media）丢失 | 演示可接受；要永久保存需接对象存储（Cloudinary / S3） |
| 每月 750 实例小时 | 单实例 24×7 ≈ 730 小时，够用 | 别建第二个免费服务 |
| Neon 空闲挂起 | 首次查询多约 0.5 秒 | 可忽略 |
| 免费额度 | Neon 0.5GB 存储，演示数据几 MB | 够用 |

---

## 7. 与本地 MySQL 的关系

| 环境 | 数据库 | 启动方式 |
|---|---|---|
| 本地开发 / 答辩演示 | MySQL 8（本机） | `DB_ENGINE=mysql`，见 `.env` |
| 线上（Render） | PostgreSQL（Neon） | `DB_ENGINE=postgres` + `DATABASE_URL` |

切换只靠环境变量，`settings.py` 三个分支：`sqlite` / `mysql` / `postgres`。
模型层没有写死任何数据库方言，`select_for_update()`、联合唯一约束、事务在两种引擎上都成立。
