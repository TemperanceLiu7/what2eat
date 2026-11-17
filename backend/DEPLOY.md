# 后端部署指南（Django + PostgreSQL）

本指南配套 `render.yaml`，把 `backend/` 这套 Django 服务部署到云端，并让 Cloudflare Pages 上的前端从 mock 数据切换到真接口。

**已验证**（本机 Python 3.14 + Django 5.2.19）：`manage.py check` 0 issues、9 张表迁移成功、`manage.py test core` 33 个用例全绿、前端 `vite build` 构建通过。

---

## 一、路线选择

`settings_prod.py` 强制要求生产库为 MySQL 或 PostgreSQL（用 SQLite 会直接报错退出），所以必须配一个云数据库。三个方案按省心程度排序：

| 方案 | 数据库 | 优点 | 注意 |
| --- | --- | --- | --- |
| **A. Render（推荐）** | Render 内置免费 Postgres | 有 `render.yaml` 蓝图，一键建库+建服务；自动注入 `DATABASE_URL` | 免费实例 15 分钟无请求会休眠，首次访问等 30~60 秒；内置库 90 天后需导出 |
| B. Render/Railway + Neon | Neon 免费 Postgres | 数据库与计算分离，库不会被回收；Neon 免费额度长期可用 | 要手动复制连接串 |
| C. 自有云服务器 | 自建 MySQL/PostgreSQL | 完全可控，不休眠 | 要自己配 Nginx/HTTPS/备份 |

下面按**方案 A** 写完整步骤，方案 B 只有一处不同（第 3 步换成手填 `DATABASE_URL`），步骤里已标注。

---

## 二、部署后端（方案 A：Render 蓝图）

### 1. 提交代码

先把本次新增的 4 个部署文件 commit 进仓库并 push 到 `main`：

```
render.yaml                    # Render 蓝图（仓库根目录）
backend/requirements-cloud.txt # 云端依赖（只装 psycopg，避开 mysqlclient 编译坑）
backend/runtime.txt            # 锁定 Python 3.12.7
backend/Procfile               # 备用启动命令（手动建服务时用）
```

这 4 个文件都不在 `.gitignore` 排除范围内，`git add` 即可。

### 2. 创建 Blueprint

1. 登录 <https://dashboard.render.com>（GitHub 账号可直接登录）
2. **New +** → **Blueprint** → 选 `Ares5807/what2eat` 仓库
3. Render 读到 `render.yaml`，自动创建：
   - 数据库 `what2eat-db`（免费 Postgres）
   - Web 服务 `what2eat-api`，并把 `DATABASE_URL` 自动注入环境变量
4. 点 **Apply**，等构建（约 3~5 分钟）

构建命令已写在蓝图里，等价于：

```bash
pip install -r requirements-cloud.txt
python manage.py collectstatic --no-input
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60
```

> **为什么不用 `requirements-prod.txt`**：里面的 `mysqlclient` 需要系统级 MySQL 头文件，在 Render 的 Python 环境里常编译失败。`requirements-cloud.txt` 只装 `psycopg[binary]`（预编译 wheel），零系统依赖。

### 3. 初始化数据库（已自动化，不用 Shell）

> **免费档没有 Shell**（只有付费实例才有 Shell / 一次性任务），所以建表与灌数据
> **不能靠手工执行**。现在全部写在 `render.yaml` 的 `startCommand` 里：

```
python manage.py migrate --no-input && python manage.py bootstrap && gunicorn config.wsgi:application ...
```

- `migrate`：建 9 张表
- `bootstrap`：幂等导入 6 个档口 / 16 道菜 / 3 条学籍，并按环境变量建后台账号
- 三条命令都能重复执行，每次部署或重启都安全（已实测连跑两次，数据不重复）

后台账号在 **Environment → ADMIN_PASSWORD** 里填（蓝图里已声明为 `sync:false`，
部署时 Render 会让你填）。没填就不建账号，不会出现默认弱口令。

> **为什么不用 `preDeployCommand`**：那是付费实例才有的能力，免费档写进蓝图会直接
> 导致部署失败。这也是之前那版手册最容易踩的一步。

### 4. 验证后端

浏览器打开（把 `<服务名>` 换成你的实际域名）：

| 地址 | 期望结果 |
| --- | --- |
| `https://<服务名>.onrender.com/api/health/` | `{"ok":true,"data":{"database":"up","dishes":16,...}}` |
| `https://<服务名>.onrender.com/api/dishes/` | 返回 `{"ok":true,"data":{"items":[...]}}`，16 个菜品 |
| `https://<服务名>.onrender.com/api/dishes/random/?source=canteen` | 返回一道食堂菜 |
| `https://<服务名>.onrender.com/api/docs/` | Swagger 接口文档 |
| `https://<服务名>.onrender.com/admin/` | Django 后台登录页 |

`/api/health/` 是蓝图里配的 `healthCheckPath`：它会真连一次数据库，库没通返回
**503**，Render 会判定这次部署失败并保留上一个可用版本，不会出现"页面活着但库里没表"。

> 免费版首次访问会冷启动，等 30~60 秒；之后正常。

---

## 三、前端切到真接口（Cloudflare Pages）

前端默认走 mock（数据在浏览器 localStorage）。切真接口只需在 Pages 加两个环境变量：

1. Cloudflare 控制台 → **Workers & Pages** → `what2eatt` → **Settings** → **Environment variables**
2. 给 **Production** 加两条：

| 变量 | 值 |
| --- | --- |
| `VITE_API_BASE` | `https://<服务名>.onrender.com/api` |
| `VITE_USE_MOCK` | `false` |

3. **Deployments** → 最新一条 → **Retry deployment**（环境变量在构建时注入，必须重新构建才生效）
4. 打开 <https://what2eattt.pages.dev>，用真实账号注册 → 学号核验 → 摇一摇，数据能存住、换设备还在，就说明接通了

> 注意 `VITE_API_BASE` 末尾不要带斜杠，`client.js` 会自己拼路径。

---

## 四、图片识别（可选）

`/api/recognize/` 走 OpenAI 兼容接口，**不配也能用**——接口返回 `ready:false`，前端自动降级成手动填菜名，打卡流程不受影响。

要开启识别，在 Render 服务 → **Environment** 加：

| 变量 | 值 |
| --- | --- |
| `LLM_API_KEY` | 你的 API Key（蓝图里已设 `sync:false`，不会进仓库） |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1`（已默认） |
| `LLM_MODEL` | 视觉模型名，如 `deepseek-chat`（已默认） |

> ⚠️ 识别要传图片给模型，必须是**支持视觉输入**的模型。若模型不支持图片，接口会报错，前端同样降级为手动填写。

---

## 五、四个必须知道的运维点

1. **上传的图片存在实例本地 `media/`，Render 免费实例重启会丢。** 打卡图片要长期保留，得接对象存储（Cloudflare R2 / 七牛 / 阿里 OSS）——改 `core/images.py` 的落盘逻辑 + `settings_prod.py` 的 `STORAGES["default"]` 即可，接口契约不用动。答辩演示阶段可以先不管。
2. **CORS 白名单已预设** `https://what2eattt.pages.dev` 和 `https://what2eatt.pages.dev`（仓库 README 里的线上地址与你给的地址差一个 `t`，两个都放进去了）。以后加自定义域名，记得同步改 Render 的 `CORS_ALLOWED_ORIGINS` 和 `CSRF_TRUSTED_ORIGINS`，否则前端会被浏览器拦掉。
3. **`ALLOWED_HOSTS` 现在是 `.onrender.com,localhost`**（子域通配）。换域名必须同步修改，否则 Django 返回 400。
4. **免费档的两个硬限制**：① 15 分钟无流量就休眠，首个请求要等 30~60 秒（前端已在启动时预热 `/api/health/`，并给了"可能正在冷启动"的提示）；② 免费 Postgres 有有效期，到期前务必导出，长期用建议按第七节换 Neon。

---

## 六、本次改动清单

### 后端（数据库真正落地）

| 文件 | 改动 |
| --- | --- |
| `render.yaml` | **删掉 `preDeployCommand`**（免费档不支持，会直接部署失败）；`migrate + bootstrap` 移入 `startCommand`；`healthCheckPath` 改指 `/api/health/`；新增 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 环境变量 |
| `core/management/commands/bootstrap.py` | **新增**。一次完成「演示数据 + 学籍 + 后台账号」，幂等，可挂到启动命令里（免费档没 Shell，必须自动化） |
| `core/views.py` | 新增 `HealthView`：`SELECT 1` 探库，库不通返回 503 |
| `core/urls.py` | 注册 `/api/health/` |

### 前端（去 AI 味 + 冷启动适配）

| 文件 | 改动 |
| --- | --- |
| `src/styles/global.css` | 设计令牌整体重做：纸底墨字、朱红点缀、小圆角、**去掉渐变/光晕/投影**；标题改衬线、数字改等宽；`chip` 从渐变胶囊改为方形 tab；组件库按钮统一在全局覆盖 |
| `src/pages/Home.vue` | 重写抽签面板与结果卡：去掉扫光、呼吸光晕、模糊+回弹动画、emoji；改为菜单卡片式排版（虚线内框、`·` 分隔的元信息行、等宽热度） |
| `src/layouts/PcShell.vue`／`MobileShell.vue` | 品牌 emoji 换成方章字标；去掉毛玻璃导航；菜单选中改墨色下划线 |
| `src/ui/UButton.vue` | 主按钮改墨黑实底、方角、无投影 |
| `src/pages/Personal.vue`／`Community.vue`／`Me.vue`／`Checkin.vue`／`Vote.vue`／`Eat.vue` | 清掉残留渐变、彩色方块、胶囊圆角、emoji、糖水底色；统一走令牌 |
| `src/api/client.js`／`errors.js`／`main.js` | 超时 10s→20s；启动时预热 `/api/health/`（应对免费档休眠冷启动）；超时文案改成"可能正在冷启动" |

## 七、方案 B 的差异（Neon 数据库）

只有第 2~3 步不同：

1. 到 <https://neon.tech> 建免费项目，复制连接串（形如 `postgresql://user:pass@ep-xxx-pooler.us-east-2.aws.neon.tech/dbname?sslmode=require`）
2. Render 建 **Web Service**（不用 Blueprint）：Root Directory 填 `backend`，Runtime 选 Python，Build/Start 命令抄第 2 步那三行
3. 环境变量手动填：`DJANGO_ENV=prod`、`DB_ENGINE=postgres`、`DATABASE_URL=<Neon 连接串>`、`SECRET_KEY=<随机 64 位>`、`ALLOWED_HOSTS=.onrender.com`、`CORS_ALLOWED_ORIGINS=https://what2eattt.pages.dev`
4. 其余（建表、seed、前端切接口）与方案 A 完全相同

生成 `SECRET_KEY`：

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> 连接串里带 `-pooler` 时，`settings.py` 会自动关掉 psycopg 的会话级预编译语句，Pooled / Direct 两种连接都能跑，不用额外配置。
