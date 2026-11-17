# 部署清单：Railway（后端）+ Neon（PostgreSQL）

> **平台选型结论（都实测过，不走代理）**
>
> | 平台 | 结果 |
> | --- | --- |
> | Render | ❌ `render.com` / `api.render.com` / `*.onrender.com` 直连超时，登录报 "We couldn't reach Render"，部署出来也没法访问 |
> | Koyeb | ❌ 2026-02 并入 Mistral AI 后**新注册用户不再有免费额度**（只有 Pro $29/月起），新账号进控制台只有一行公告，建不了服务 |
> | **Railway** | ✅ `railway.com`、`backboard.railway.app`、`*.up.railway.app` 全部直连可达；新用户 **30 天 $5 试用额度、不需要信用卡** |
> | Neon | ✅ 数据库已建好，直连可达（本文沿用） |
>
> 代码一行不用改：`Dockerfile` 已经在仓库根目录，Railway 会自动识别。

**总耗时约 15 分钟**：建服务 3 分钟 → 填变量 3 分钟 → 构建 5 分钟 → 验收 2 分钟。

---

## 0. 前置条件

| 需要 | 说明 |
| --- | --- |
| 代码已 push | 仓库根目录要有 `Dockerfile`，`backend/core/management/commands/bootstrap.py` 也要在 |
| Neon 连接串 | 上一步 `console.neon.tech` → Connect → 勾 Pooled → 复制的 `postgresql://...?sslmode=require` |
| GitHub 账号 | 就是 `Ares5807`（仓库是私有的，Railway 会要求授权访问） |

---

## 1. Railway 注册（2 分钟）

1. 打开 <https://railway.com> → 右上 **Login** → **Login with GitHub**
2. 第一次会让你授权 Railway 的 GitHub App：选 **Only select repositories** → 勾 `what2eat`
3. 登录后是空的 Dashboard，正常。**不需要填信用卡**，注册即送 30 天 $5 额度

> 免费额度能撑多久：小服务（0.5 GB 内存、0.1 vCPU）24 小时不睡约 $7/月，$5 大概 3 周。
> 第 5 步开启「App Sleeping」后，没流量时不计费，同一份额度能撑几个月，够答辩用。

---

## 2. 建服务（3 分钟）

1. 点 **New Project** → **Deploy from GitHub repo** → 选 `Ares5807/what2eat`
2. Railway 会自动扫描仓库：根目录有 `Dockerfile` 时，Builder 会显示 **Dockerfile**，不用改
3. 服务创建后立刻开始构建，先别管它，去做第 3 步

> 如果它误判成 Nixpacks：进服务 → **Settings** → **Build** → Builder 改成 **Dockerfile**，Path 留 `Dockerfile`。

---

## 3. 填环境变量（3 分钟）

服务页 → **Variables** → 右上 **RAW Editor**，把下面整段粘进去，再把三个 `<...>` 替换掉：

```
DJANGO_ENV=prod
SECRET_KEY=<粘贴 50 位随机串>
DB_ENGINE=postgres
DATABASE_URL=<粘贴 Neon 连接串>
ALLOWED_HOSTS=.up.railway.app,localhost
CORS_ALLOWED_ORIGINS=https://what2eattt.pages.dev,https://what2eatt.pages.dev
CSRF_TRUSTED_ORIGINS=https://what2eattt.pages.dev,https://what2eatt.pages.dev
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<你自己定的后台密码>
LLM_API_KEY=<你的模型 Key，可不填>
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
PYTHONUNBUFFERED=1
```

生成 `SECRET_KEY`（PowerShell）：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

- `LLM_API_KEY` 不填也能跑：`/api/recognize/` 会降级成手动填菜名
- 两个 `ORIGINS` 必须写完整 `https://域名`，**不能带结尾斜杠**
- 粘完点 **Save**，Railway 会自动重新部署一次

---

## 4. 开域名 + 对端口（2 分钟）

1. 服务页 → **Settings** → **Networking** → **Public Networking** → **Generate Domain**
2. 端口填 **8000**（我们的 `gunicorn` 绑 `$PORT`，缺省 8000；若 Railway 在 Variables 里已自动注入 `PORT`，就填它的值，两个保持一致即可）
3. 生成后拿到 `https://what2eat-api-production-xxxx.up.railway.app` 这样的域名
4. **Settings** → **Region** 选 **US East (Virginia)** —— 和 Neon 的 `us-east-1` 同区，数据库往返延迟最低

> 健康检查不用填，Railway 以「端口能连上」为准。若想填 Path，用 `/api/health/`。

---

## 5. 省钱开关（30 秒，强烈建议）

**Settings** → **Serverless**（或 Deploy 里的 App Sleeping）→ 打开。
没流量 5 分钟后自动休眠，请求来了再唤醒（冷启动 5~10 秒，答辩演示前先打开一次预热）。

---

## 6. 看构建日志

**Deployments** → 最新一条 → **View Logs**，应依次出现：

```
Successfully installed Django-5.2.x psycopg-3.x gunicorn-x whitenoise-x
154 static files copied ... 444 post-processed
Applying core.0001_initial... OK
档口 6 家 / 菜品 16 道 / 学籍 3 条
[2/2] 后台账号 已创建后台账号 admin
Booting worker with pid ...
```

---

## 7. 验收后端（2 分钟）

| 打开 | 期望 |
| --- | --- |
| `https://<你的域名>/api/health/` | `{"ok":true,"data":{"database":"up","dishes":16,"shops":6}}` |
| `https://<你的域名>/api/dishes/` | 16 道菜 |
| `https://<你的域名>/api/docs/` | Swagger 能打开 |
| `https://<你的域名>/admin/` | `admin` + 你设的密码能登录 |

返回 503 说明库没通：看日志里 `migrate` 那一段。`dishes:16` 说明 `bootstrap` 已经把数据灌进 Neon 了。

---

## 8. 前端切真接口（3 分钟）

当前实际采用 **Netlify 直传**（当天 Cloudflare 控制台处于 Partially Degraded Service，且新版控制台把
Workers & Pages 拆到了 Build → Compute，入口难找）。两条路选一条即可。

### 路线 A：Netlify 直传（已采用，最快）

1. 本地构建，接口地址在**构建时**固化进产物：

   ```bash
   cd what2eat
   VITE_API_BASE="https://<你的后端域名>/api" VITE_USE_MOCK=false npx vite build
   ```

2. 把 `dist/` 打成 zip（**压缩包根目录必须直接是 `index.html`**，不能多套一层 `dist/`）
3. 打开 <https://app.netlify.com/drop>，拖进去；未登录可先用邮箱注册，不必用 GitHub 登录
4. 进入站点 → **总览页顶部青色的 `Make public` 按钮** → 确认

> **必踩的坑**：Netlify 2026 新建站点默认 **Visitor access = Private**，只有登录该团队的人能看，
> 匿名访问 `/`、`/index.html`、`/assets/` 全部 401，响应头指向 `app.netlify.com/edge-access`。
> 开关**不在**团队 Settings，也**不在** Project configuration 里，就是总览页那个 `Make public` 按钮。
> 下面那张「Protect and secure access / Upgrade to protect」是 Pro 套餐的密码保护推销卡，不要点。
>
> **验收必须用匿名 curl**，你浏览器里能打开不算数——你的会话带着团队登录态，天然能过这道门：
>
> ```bash
> curl -s -o /dev/null -w "%{http_code}\n" https://<站点>.netlify.app/
> # 要 200；再测一个深链接，验证 SPA 回退：/eat 也要 200
> ```

### 路线 B：Cloudflare Pages（push 自动构建）

1. Cloudflare → **Workers & Pages** → 你的项目 → **Settings** → **Environment variables** → **Production**
2. 两条：

   | 变量 | 值 |
   | --- | --- |
   | `VITE_API_BASE` | `https://<你的域名>/api`（**结尾不要斜杠**） |
   | `VITE_USE_MOCK` | `false`（必须正好是 `false`） |

3. **Deployments** → 最新一条右侧 `...` → **Retry deployment**（Vite 变量构建时注入，不重建不生效）

### 跨域（两条路线都要做一次）

后端必须放行前端域名，否则浏览器收到 204 预检但**一个 `access-control-*` 头都没有**，请求直接被拦。
后端已内置正则，`.netlify.app` / `.pages.dev` / `.vercel.app` 三类平台域名自动放行，换站点不用改代码；
自定义域名仍需把 `CORS_ALLOWED_ORIGINS` 设成 `https://<域名>`（精确匹配、不带尾斜杠）。

**验收**：F12 → Network 能看到 `/api/health/`、`/api/dishes/random/` 的 200；抽到的菜与 `/admin/core/dish/` 一致；
**换手机/换浏览器再抽，收藏和打卡还在** ← 这条才证明真进库了。

---

## 9. 常见坑

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 构建失败 `No module named 'psycopg'` | Builder 用了 Nixpacks + `requirements.txt` | Builder 改成 **Dockerfile** |
| 启动即退出，`生产环境必须设置环境变量 SECRET_KEY` | 漏了 `SECRET_KEY` | 补 50 位随机串 |
| 域名打开 404 / 502 | 域名指向的端口和应用监听的端口不一致 | Networking 里的端口与 `PORT` 变量对齐，缺省都用 8000 |
| 400 `DisallowedHost: Invalid HTTP_HOST header: 'healthcheck.railway.app'` | Railway 存活探针固定用这个 Host 打容器，和业务域名无关；白名单只写业务域名就把它挡在外面，平台一直判定实例不健康 | 已由 `backend/config/settings.py` 自动并入 `healthcheck.railway.app`、`RAILWAY_PUBLIC_DOMAIN` 与 `.up.railway.app` 后缀，**无需再配变量**；旧版代码需在 `ALLOWED_HOSTS` 里补 `.up.railway.app,healthcheck.railway.app` |
| 改完代码重新部署，但部署记录一直停在某条**旧提交**上，Build 只花几秒 | Railway 的 **Source Repo** 指向的是 fork（如 `TemperanceLiu7/what2eat`），而 `git push` 推的是上游团队仓库（`Ares5807/what2eat`），两边不是同一个仓库 | Settings → Source 里那个仓库必须和实际推送的地址一致。本仓库已把 `origin` 配成一次推两个仓库：`git remote set-url --add --push origin <仓库A>` + `git remote set-url --add --push origin <仓库B>` |
| Deploy Logs 只有一行 `No migrations to apply.`，之后无声无息，健康检查一直失败 | Settings → Deploy 里的 **Custom Start Command** 非空，覆盖了镜像的 `ENTRYPOINT`，迁移跑完进程就退出 | 清空 Custom Start Command → Redeploy。启动链写在 `docker-entrypoint.sh`，命令行里不该再填任何东西 |
| 接口 500 `relation "core_dish" does not exist` | 没建表 | 启动命令里必须 `migrate --no-input` |
| `/admin/` 样式全丢 | collectstatic 没跑 | Dockerfile 里那一步不能删 |
| 前端报 CORS，预检 204 但没有任何 `access-control-*` 头 | `CorsMiddleware` 只做精确匹配，前端换域名后 Origin 不在白名单 | 已内置正则，`.netlify.app` / `.pages.dev` / `.vercel.app` 自动放行；自定义域名把 `CORS_ALLOWED_ORIGINS` 设成 `https://<域名>`（无尾斜杠） |
| 站点能自己打开，别人打开是 Netlify 登录页 / 401 | 新建站点默认 **Visitor access = Private** | 项目总览页顶部点青色 `Make public`，立即生效，不用重新部署；验收必须用匿名 curl |
| 接口很慢（>1s） | 应用与数据库跨区 | Region 选 **US East (Virginia)**，与 Neon 同区 |
| 试用额度用光 | 服务常驻不休眠 | 开 App Sleeping；或升级 Hobby $5/月 |

---

## 10. 一句话总结

> 换平台只是换了「跑在哪台机器上」：`DATABASE_URL` 指到数据库，容器里 `migrate + bootstrap + gunicorn`，
> `/api/health/` 一返回 `database: up` 就算通，前端把 `VITE_API_BASE` 指过去即可。

本次实际落地（2026-11-17）：

- 前端 <https://what2eat-campus.netlify.app>（Netlify 直传 `dist`）
- 后端 <https://what2eat-api-production.up.railway.app>（Railway Docker + gunicorn）
- 数据库 Railway PostgreSQL，容器启动自动迁移 + 种子（6 档口 / 16 菜）
