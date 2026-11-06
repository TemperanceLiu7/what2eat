# 今天吃什么 · Django + DRF 后端

校园「今天吃什么」随机推荐系统的后端。前端（Vue 3，`../src`）已存在，本目录是**从零搭建**的
Django 5 + DRF + MySQL 服务，接口路径与返回结构严格对齐前端契约层
（`../src/api/README.md`、`../src/api/index.js`）。

- 技术栈：Django 5 + Django REST Framework + SimpleJWT + drf-spectacular
- 数据库：本地 SQLite（零安装）/ 生产 MySQL 8（`DB_ENGINE` 切换）
- 图片：本地 `MEDIA_ROOT`，生产可换对象存储
- 配置：全部走环境变量，模板见 `.env.example`

---

## 一、快速开始（本地，SQLite）

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

cp .env.example .env          # Windows: copy .env.example .env（不改也能跑，dev 有默认值）

python manage.py migrate
python manage.py seed         # 6 个档口 + 16 个菜品 + 3 条学籍
python manage.py seed --admin # 可选：再建后台账号 admin / admin123456
python manage.py runserver    # http://127.0.0.1:8000
```

- 接口：`http://127.0.0.1:8000/api/...`
- 文档：`http://127.0.0.1:8000/api/docs/`（Swagger UI）· `http://127.0.0.1:8000/api/schema/`
- 后台：`http://127.0.0.1:8000/admin/`

前端切换真接口：在**前端目录**新建 `.env.local`（本仓库没有改任何前端文件）：

```dotenv
VITE_API_BASE=http://127.0.0.1:8000/api
VITE_USE_MOCK=false
```

改完重启 `pnpm dev`。跨域已由 `config/middleware.py` 里自带的最小 CORS 中间件处理
（开发环境默认放开全部来源），不需要再配 Vite proxy。

---

## 二、目录结构

```
backend/
├── manage.py                  # 入口；DJANGO_ENV=dev|prod 决定加载哪套 settings
├── requirements.txt           # 基础依赖（SQLite 开发）
├── requirements-prod.txt      # 生产额外依赖（mysqlclient / gunicorn）
├── .env.example               # 环境变量模板
├── .gitignore
├── README.md
├── smoke_test.py              # 联调冒烟：对已启动的服务跑真实 HTTP 全链路（标准库实现）
├── config/
│   ├── settings.py            # 基础配置（dev/prod 共用）
│   ├── settings_dev.py        # 开发：SQLite、DEBUG=True、宽松 CORS
│   ├── settings_prod.py       # 生产：MySQL、强制 DEBUG=False、安全响应头、CORS 白名单
│   ├── middleware.py          # 最小 CORS 中间件（不引 django-cors-headers）
│   ├── urls.py                # /admin /api /api/schema /api/docs /media
│   ├── wsgi.py / asgi.py
├── core/                      # 唯一业务 app（9 张表都在这）
│   ├── models.py              # 9 个 model
│   ├── admin.py               # 菜品维护 / 举报审核 / 禁言解禁
│   ├── serializers.py         # 输出含 camelCase 别名，输入做严格校验
│   ├── views.py               # 全部接口
│   ├── urls.py                # 路由
│   ├── responses.py           # 统一信封 ok/fail + ApiError + 全局 exception_handler
│   ├── pagination.py          # EnvelopePagination → {items,total,page,...}
│   ├── permissions.py         # ensure_verified / ensure_can_publish
│   ├── authentication.py      # OptionalJWTAuthentication（公开接口容忍过期 token）
│   ├── schema.py              # drf-spectacular 认证方案扩展
│   ├── images.py              # base64 data URL → ImageField 文件
│   ├── tests.py               # 28 个接口自检用例
│   ├── migrations/0001_initial.py
│   └── management/commands/seed.py
├── media/                     # 上传的图片（gitignore）
└── staticfiles/               # collectstatic 输出（gitignore）
```

数据库表名通过 `Meta.db_table` 固定为：`users`、`shops`、`dishes`、`checkins`、`likes`、
`favorites`、`reports`、`votes`、`votes_records`。

---

## 三、环境变量

| 变量 | 默认（dev） | 说明 |
| --- | --- | --- |
| `DJANGO_ENV` | `dev` | `dev` / `prod`，决定加载哪套 settings |
| `SECRET_KEY` | dev 内置弱密钥 | **生产必填**，缺失直接启动失败 |
| `DEBUG` | `True` | 生产被强制 `False` |
| `ALLOWED_HOSTS` | `*`（dev） | 逗号分隔；**生产必填** |
| `DB_ENGINE` | `sqlite` | `sqlite` / `mysql` |
| `DB_NAME` `DB_USER` `DB_PASSWORD` `DB_HOST` `DB_PORT` | — | MySQL 连接信息 |
| `DB_SQLITE_PATH` | `backend/db.sqlite3` | SQLite 文件位置 |
| `CORS_ALLOWED_ORIGINS` | `127.0.0.1:5173`、`localhost:5173` | 前端来源白名单，逗号分隔 |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | `120` / `7` | 令牌有效期 |
| `API_PAGE_SIZE` | `10` | 列表默认每页条数 |
| `RECOMMEND_RECENT_LIMIT` | `4` | 随机推荐排除最近 N 条打卡 |
| `RECOMMEND_WEIGHT_BASE` / `RECOMMEND_WEIGHT_HEAT` | `1.0` / `0.06` | 加权随机参数 |
| `VOTE_DEFAULT_HOURS` | `12` | 投票默认时长 |
| `VOTE_TARGET_COUNT_MIN` / `MAX` | `2` / `99` | 目标人数区间 |
| `AUTO_MUTE_REPORT_COUNT` / `AUTO_MUTE_HOURS` | `5` / `24` | 举报达到 N 次自动禁言 N 小时 |
| `IMAGE_MAX_BYTES` | `5242880` | 单张图片上限（5MB） |
| `TIME_ZONE` | `Asia/Shanghai` | 时区（`USE_TZ=True`，库里存 UTC） |

`.env` 由 `config/settings.py` 里 20 行的极简解析器读取，**没有** python-dotenv 依赖；
真实环境变量优先级高于 `.env`。

---

## 四、数据模型（9 张表）

| 表 | 关键字段 | 说明 |
| --- | --- | --- |
| `users` | `student_id`(unique, null) `name` `college` `role`(student/admin) `status`(normal/muted/banned) `ban_until` `report_count` | 继承 `AbstractUser`；`AUTH_USER_MODEL="core.User"` |
| `shops` | `name` `type`(canteen/takeout/restaurant/night) `location` `image` `status` | 档口 |
| `dishes` | `shop`(FK) `name` `image` `description` `price`(decimal) `category` `likes` `favorites` | 菜品；`(shop,name)` 唯一 |
| `checkins` | `user`(FK) `content` `image` `dish`(FK null) `created_at` | 打卡 |
| `likes` | `user` `target_type` `target_id` | 联合唯一 `(user,target_type,target_id)` |
| `favorites` | 同上 | 同上 |
| `reports` | `reporter` `reported` `target_type` `target_id` `reason` `status`(pending/approved/rejected) `result` `created_at` | 举报 |
| `votes` | `creator` `title` `target` `status`(ongoing/passed/rejected/expired) `deadline` `target_count` `agree_count` `disagree_count` `created_at` | 投票 |
| `votes_records` | `vote`(FK) `user`(FK) `option`(agree/disagree) | 联合唯一 `(vote,user)` 防刷票 |

派生属性（不加字段）：
- `User.is_verified` = 学号已落库；`User.is_muted` / `is_banned` 会判断 `ban_until` 是否过期。
- `Vote.need` = `target_count // 2 + 1`；`Vote.settle()` 结算状态。

---

## 五、接口

统一返回：成功 `{"ok": true, "data": {...}, "message": ""}`；
失败 `{"ok": false, "code": "XXX", "message": "中文提示"}`。
认证：`Authorization: Bearer <access>`。

| 方法 | 路径 | 认证 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/auth/register/` | 否 | 注册，返回 access/refresh/token + user |
| POST | `/api/auth/token/` | 否 | 登录（账号或学号都行） |
| POST | `/api/auth/token/refresh/` | 否 | 刷新 access |
| POST | `/api/auth/bind-student/` | 是 | 学号+姓名+学院 三重核验并绑定 |
| GET | `/api/dishes/random/?source=` | 可选 | 加权随机单条；`source=all/canteen/takeout/restaurant/night` |
| GET | `/api/dishes/` | 可选 | 分页列表，支持 `source/shop/category/search/ordering` |
| POST | `/api/checkins/` | 是 | 发布打卡（需已核验且未禁言） |
| GET | `/api/checkins/` | 可选 | 分页列表，支持 `mine/dish/search` |
| POST | `/api/likes/toggle/` | 是 | 点赞/取消，`{target_type,target_id}` |
| POST | `/api/favorites/toggle/` | 是 | 收藏/取消 |
| GET | `/api/favorites/` | 是 | 我的收藏（菜品类展开成菜品对象） |
| POST | `/api/reports/` | 是 | 举报 `{reported_id,target_type,target_id,reason}` |
| POST | `/api/votes/` | 是 | 发起投票 `{title,target,target_count}` |
| POST | `/api/votes/{id}/cast/` | 是 | 投票 `{option:"agree"|"disagree"}` |
| GET | `/api/votes/` | 可选 | 分页列表，带 `my_option`，支持 `status/mine` |

列表响应的 `data` 固定为 `{items,total,page,page_size,pages}`。

错误码（HTTP 状态见括号）：

| code | 状态 | 场景 |
| --- | --- | --- |
| `UNVERIFIED` | 403 | 未绑定学号就打卡 / 发投票 / 举报 |
| `BANNED` | 403 | 禁言 / 封禁中 |
| `ALREADY_VOTED` | 409 | 同一人重复投票 |
| `VOTE_CLOSED` | 409 | 投票已结束 / 已截止 |
| `INVALID_DATA` | 400 | 参数缺失、格式错误、对象不存在、重复举报 |
| `UNAUTHORIZED` | 401 | 未登录 / token 失效 |
| `FORBIDDEN` | 403 | 已登录但无权限 |
| `NOT_FOUND` | 404 | 资源不存在（随机推荐该来源无菜也走它） |

### 四条核心接口的实现要点

**`POST /api/auth/bind-student/`** —— 三重核验
1. 用 `student_id + name + college` 三列**同时匹配** `users` 表里的学籍记录，任一不符 → `INVALID_DATA`；
2. 在 `transaction.atomic()` + `select_for_update()` 中处理，避免并发抢绑；
3. 命中的是 seed 生成的「学籍占位账号」（无可用密码、非员工）→ 删除占位行，把学号写进当前账号；
4. 命中真实账号 → `该学号已被其他账号绑定`（`student_id` 的 unique 约束兜底）；
5. 同一账号重复核验同一学籍 → 幂等通过；换绑其他学号 → 提示联系管理员。

**`GET /api/dishes/random/?source=canteen`** —— 加权随机
1. 候选池 = 该来源下 `shop.status=open` 的菜品；
2. 已登录用户取最近 `RECOMMEND_RECENT_LIMIT`（默认 4）条打卡的 `dish_id` 从池中剔除；
3. 若剔除后为空（都吃过了）退回完整池，保证一定抽得到；
4. 权重 `w = 1 + (likes + favorites) * 0.06`，用 `random.choices` 按权重抽 1 条；
5. 返回 `data.dish`，附带 `source`、`poolSize`、`excludedCount`、本次权重；该来源没菜 → 404 `NOT_FOUND`（前端当作「没抽到」）。

**`POST /api/checkins/`** —— 打卡
1. `ensure_can_publish`：未登录 401、未核验 `UNVERIFIED`、禁言/封禁 `BANNED`；
2. `content` 去空白后非空、≤ 500 字；`dish_id`/`dish_name` 可关联已有菜品；
3. `image` 支持 `data:image/...;base64,...`（Pillow 校验真实格式、大小上限 `IMAGE_MAX_BYTES`），落盘到 `MEDIA_ROOT/checkins/%Y/%m/`；
4. 返回 `data.checkin`（含 `id`、`at` 毫秒时间戳）。

**`POST /api/votes/{id}/cast/`** —— 投票
1. `ensure_can_publish`；`option` 只接受 `agree|disagree`；
2. 先做廉价预检（不存在 404 / 已结束或过期 `VOTE_CLOSED` / 已投 `ALREADY_VOTED`）；
3. 进 `transaction.atomic()` 后 `select_for_update()` 重新校验一遍，插入 `votes_records`；
4. 唯一约束 `(vote,user)` 兜底并发双击，`IntegrityError` 翻译成 `ALREADY_VOTED`；
5. 计票后 `settle()`：`need = floor(target_count/2)+1`，`agree>=need → passed`、`disagree>=need → rejected`；
6. 返回更新后的 `data.vote`（含 `need`、`status`、`my_option`）。

---

## 六、后台管理（/admin/）

- **菜品维护**：`ShopAdmin` 内联菜品；`DishAdmin` 支持搜索/筛选/行内改价，批量操作
  「重新统计点赞收藏数」「重置热度」。
- **举报审核**：`ReportAdmin` 批量「通过举报（计入违规次数）」「通过举报并禁言 3 天」「驳回举报」；
  通过时累加被举报人 `report_count`，达到 `AUTO_MUTE_REPORT_COUNT` 自动禁言。
- **禁言 / 解禁**：`UserAdmin` 批量操作「禁言 1/3/7 天」「封禁（长期）」「解禁 / 恢复正常」，
  写 `status` + `ban_until`；到期后自动失效，无需定时任务。

---

## 七、自检

```bash
python manage.py check                              # System check identified no issues (0 silenced)
python manage.py makemigrations --check --dry-run   # No changes detected
python manage.py test                               # 28 个用例全部通过
python manage.py seed                               # 6 档口 / 16 菜品 / 3 学籍
python manage.py spectacular --file schema.yaml --fail-on-warn   # 13 条路径，0 warning
python smoke_test.py --base http://127.0.0.1:8000/api           # 真实 HTTP 全链路 29 项
```

`core/tests.py`（隔离测试库）覆盖：注册登录、三重核验（含重复绑定、未登录）、随机推荐的 source 过滤 /
空来源 404 / 最近 4 条打卡排除、打卡的未核验 / 禁言 / 空内容 / 正常发布、点赞收藏的计数增减与唯一约束、
收藏列表展开、投票的过半通过 / 过半否决 / 重复投 / 过期 / 未核验、举报计数与防重复、分页信封、CORS 预检。

`smoke_test.py`（真实 HTTP + 真实库）覆盖同样的主链路：信封格式、注册后 `verified=false`、错误学院核验失败、
正确三重核验通过、随机推荐、打卡、点赞计数回落、收藏、投票 `need` 计算 / 重复投 409 / 列表回显 `my_option`、
举报参数校验、401 边界、`/api/docs/` `/api/schema/` `/admin/login/` 可达、CORS 预检 204。

本次交付时的实际结果：`check` 0 issues、`makemigrations --check` No changes detected、28 个单元测试 OK、
29 项冒烟全通过、OpenAPI 13 条路径 0 warning、admin 各页 200 且「禁言 / 解禁 / 举报通过」批量操作实测生效。

---

## 八、生产部署（MySQL 8）

```sql
CREATE DATABASE what2eat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
pip install -r requirements-prod.txt

export DJANGO_ENV=prod
export SECRET_KEY='<python -c "import secrets;print(secrets.token_urlsafe(64))">'
export ALLOWED_HOSTS=api.example.com
export CORS_ALLOWED_ORIGINS=https://what2eat.example.com
export DB_ENGINE=mysql DB_NAME=what2eat DB_USER=what2eat DB_PASSWORD=*** DB_HOST=127.0.0.1 DB_PORT=3306

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application -b 127.0.0.1:8000 -w 3
```

Nginx 侧重定向 `/static/` 与 `/media/`（生产不再由 Django 托管媒体文件）。
`settings_prod.py` 会在缺少 `SECRET_KEY` / `ALLOWED_HOSTS` / CORS 白名单或未用 MySQL 时**直接报错退出**，
避免带着开发配置上线。

> `mysqlclient` 编译失败时，可换纯 Python 驱动：`pip install PyMySQL`，并在
> `config/__init__.py` 加 `import pymysql; pymysql.install_as_MySQLdb()`。

---

## 九、与前端对接的两个注意点

1. **注册不会自动绑定学号**：注册只记账号/密码/姓名/学院，`student_id` 必须走
   `/api/auth/bind-student/` 三重核验后才落库（否则填个学号就能变「已核验」，核验形同虚设）。
   前端 mock 里注册返回 `verified:false`，行为一致。
2. **字段别名**：库里是 snake_case，序列化层额外输出 `shopId`/`desc`/`source`/`sourceLabel`/
   `targetCount`/`agree`/`disagree`/`at` 等 camelCase 别名，前端原来读 `db.js` 的模板不用改。

---

## 十、还没做 / 后续可加

- `POST /api/checkins/` 的 `dish_name` 只做「已有菜品按名匹配」，匹配不到就只存文本、不建菜品
  （避免用户随手造菜品污染数据）；如需支持「自定义菜名」，建议给 `checkins` 加一列 `dish_name`。
- 举报审核目前只有后台批量操作，没有面向用户的「我的举报进度」接口。
- 列表接口暂无 Redis 缓存与限流（`THROTTLE` 预留了 `TOO_MANY_REQUESTS` 错误码）。
- 投票没有定时任务把 `ongoing` 的过期投票刷成 `expired`，改为**惰性结算**（读列表/投票时顺手更新）。
- 图片只落本地 `MEDIA_ROOT`；换对象存储时只需替换 `core/images.py` 与 `DEFAULT_FILE_STORAGE`。
- 无「删除/编辑打卡」接口，也没有举报自动下线内容的策略（目前只累加 `report_count` + 自动禁言）。
