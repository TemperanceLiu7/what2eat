# 校园「今天吃什么」· 同址多端演示版

一个**网址**，同时给电脑和手机用：宽屏进来是 Element Plus 的桌面布局（顶部导航 + 左右分栏），窄屏或手机进来是 Vant 的移动布局（底部 TabBar + 单列卡片）。线上版本已接真实后端（Django + PostgreSQL）；本地开发时把 `VITE_USE_MOCK` 打开即可用模拟数据完整演示，不需要启动 Django。

## 线上地址

**前端**：<https://celebrated-jalebi-812a02.netlify.app>

<img src="docs/qrcode.png" alt="扫码打开" width="180" />

**后端 API**：<https://what2eat-api-production.up.railway.app/api>

- 健康检查 <https://what2eat-api-production.up.railway.app/api/health/>
- 接口文档 <https://what2eat-api-production.up.railway.app/api/docs/>
- 后台管理 <https://what2eat-api-production.up.railway.app/admin/>

线上版本走**真实后端**（构建时 `VITE_USE_MOCK=false`），数据来自 Railway 上的 PostgreSQL，种子数据 6 个档口 / 16 道菜。

部署形态：前端 Netlify 静态托管，后端 Railway（Django + gunicorn + PostgreSQL）。代码同时推送到 `Ares5807/what2eat` 与 `TemperanceLiu7/what2eat`，两个仓库内容一致。

> 原 `what2eatt.pages.dev` 的 Cloudflare Pages 站点已停用。`docs/qrcode.png` 已按当前 Netlify 地址重新生成（451×451，QR 版本 4、纠错级别 Q），若域名变更需同步重新生成。

## 本地地址

- 电脑：<http://localhost:5180>
- 手机：`http://10.6.60.42:5180`（手机和电脑连同一个 Wi-Fi）

> 服务是用 `server.mjs` 托管 `dist/` 的，纯静态、零依赖。想换端口：`PORT=8080 node server.mjs`。

## 怎么验证「同一个网址，两套界面」

1. 电脑浏览器打开线上地址或 <http://localhost:5180>，看到的是顶部横向导航 + 左推荐右人气榜。
2. 把窗口拖窄到 820px 以下（或者按 F12 → 切换设备工具栏选 iPhone），**不刷新**，会实时切成手机布局：头部变矮、底部出现 TabBar、卡片变单列。
3. 手机扫码打开线上地址，是同一个 URL、同一份代码。

切换逻辑在 `src/composables/useIsMobile.js`，用 `matchMedia('(max-width: 820px)')`，不是 UA 判断——所以 iPad 分屏、旋转屏幕都能正确响应，分享出去的链接也永远自适配当前设备。

## 演示流程（建议按这个顺序走）

1. **登录 / 注册** → 右上角「登录 / 注册」或手机端右上角「登录」。
   - mock 模式：账号 `20230001` / 密码 `123456`（点「填入演示账号」自动填），登录后自动完成核验
   - 真接口模式：先注册（账号+密码+姓名+学院），再走学号核验
2. **我的** → 未核验时会拦下来，提交学号 20230001 / 张同学 / 计算机学院完成核验。
   这一步是为了让你看到「未认证不能发布」的拦截效果，可以先不登录直接去打卡试试。
3. **随机推荐** → 选范围（食堂/外卖/饭店/夜市）→ 摇一摇。
   手机上第一次点按钮会申请动作权限，授权后可以直接甩手机抽签。
4. 抽到结果后点 👍 收藏 / ❤️ 点赞，热度会进入下一轮的加权随机。
5. **备餐打卡** → 拍照或选图 → 写两句 → 发布（会压成 900px 的 JPEG）。
6. **吃不吃投票** → 发起投票（默认 6 人，过半需 4 票）→ 自己投一票；
   mock 模式下还能点「模拟同学」把票数推到「通过」（真接口模式没有这个按钮，需要真实用户来投）。

## 登录与前后端联调

页面全部走 `src/api/` 这一层，底下是 mock 还是真 HTTP 由环境变量决定，页面代码不用改。

| 模式 | 触发条件 | 数据 |
|---|---|---|
| mock（默认） | 不配环境变量，或 `VITE_USE_MOCK` 不是 `false` | 浏览器 localStorage，线上演示站用的就是这个 |
| 真接口 | `VITE_USE_MOCK=false` + `VITE_API_BASE` | Django + MySQL/PostgreSQL |

切真接口（本地）：

```bash
# 1) 起后端
cd backend && python manage.py runserver 127.0.0.1:8000

# 2) 带环境变量构建前端
VITE_API_BASE=http://127.0.0.1:8000/api VITE_USE_MOCK=false \
  node node_modules/vite/bin/vite.js build

# 3) 打开 http://localhost:5180 就是真接口版本
```

也可以把这两个变量写进前端根的 `.env.local`（已 gitignore），`pnpm build` 时自动生效。

已联调通过（真实 Django + MySQL）：
注册 → 学号核验 → 摇一摇 → 点赞/收藏 → 发布打卡 → 发起投票 → 投票 → 我的页 → 退出登录。

> 联调用的测试账号会长占学籍（一个学号只能绑一个账号）。测试完执行
> `python backend/scripts/cleanup_e2e.py` 清理，再 `cd backend && python manage.py seed` 恢复 3 条学籍。

## 申请复审（投票的二次裁决）

对应文档 2.3.1 / 3.7 节。

**入口**：投票页，**已出结果**的投票卡片右下角出现「申请复审」。

**规则**（前后端同一套，后端为准）：

| 规则 | 说明 |
|---|---|
| 谁能申请 | 参与过这次投票的人，或发起人本人 |
| 何时能申请 | 原投票必须已出结果（通过 / 未通过 / 已截止）；进行中不行 |
| 能复审几次 | 一次。同一个投票只能被复审一次 |
| 复审的复审 | 不允许，复审投票本身不能再申请复审 |
| 人数怎么变 | `新目标 = 原目标 + max(2, 原目标 // 2)`，封顶 99（6 人 → 9 人，3 人 → 5 人） |
| 结果怎么算 | 复审独立结算，同样用「过半」规则；以复审结果为准 |

**接口**：`POST /api/votes/{id}/review/`

```json
{ "ok": true, "data": { "vote": {...}, "need": 5, "originalId": 12, "targetCount": 9 },
  "message": "已发起复审，参与人数扩大到 9 人" }
```

**数据模型**：`votes` 表新增自关联字段 `review_of`（指向被复审的原投票，普通投票为 NULL）。
迁移文件 `core/migrations/0002_vote_review_of.py`。

**前端表现**：

- 复审投票卡片标题前有蓝色「复审」标签
- 下方一行提示：「由投票 #12 复审而来，参与人数扩大到 9 人」
- 原投票被复审后，「申请复审」按钮自动消失（后端返回 `reviewedBy: true`）

**已验证**（`python manage.py test core`，33 个用例全绿）：

```
结算 passed need=2
申请复审 → 201，targetCount 3→5，need=3，isReview=true，reviewOf=原id
列表中原投票 reviewedBy=true / my_option=agree
重复申请 → 400「这个投票已经复审过了」
复审再复审 → 400「复审投票不能再申请复审」
非参与者申请 → 403 FORBIDDEN
进行中申请 → 400 INVALID_DATA
```

## 个人板块 / 社区板块

产品结构从一个平面 Tab 改成两块：

```
个人 /personal   摇一摇 · 今天吃了啥 · 我的收藏 · 口味画像 · 我的记录（含私密）
社区 /community  打卡广场（只含公开）· 投票广场
我的 /me         身份核验 · 统计 · 退出
```

导航只有三个入口：**个人 / 社区 / 我的**（`/` 会跳到 `/personal`，摇一摇在 `/draw`）。

### 打卡为什么两边都有

`checkins` 表加了 `visibility`：

| 值 | 去处 | 影响 |
|---|---|---|
| `public` | 社区打卡广场，别人能看、能点赞、能举报 | 正常社区内容 |
| `private` | 只在「个人 → 我的记录」里 | **不进社区、不可被举报**，但**一样计入个人偏好和随机推荐的去重窗口** |

所以不加入社区的同学，只靠自己记录也能让系统越用越懂他——这正是「个人偏好」的意义。

- 社区列表：`GET /api/checkins/`（默认只返回 public）
- 个人列表：`GET /api/checkins/?scope=mine`（含 private）

### 今天吃了啥（图片识别）

页面 `/eat`：拍照/选图 → **自动识别菜品** → 确认或手改 → 选「仅自己可见 / 公开到社区」→ 保存。

后端 `POST /api/recognize/`：把图片转成 data URI 交给 OpenAI 兼容的视觉接口，返回最多 3 个候选：

```json
{ "ok": true, "data": { "dishes": [{"name":"红烧肉盖饭","confidence":0.82,"category":"盖饭"}],
                        "note":"", "ready": true, "model": "deepseek-flash" } }
```

配置在 `backend/.env`（都已 gitignore）：

```bash
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TEMPERATURE=0.3
```

不配 `LLM_API_KEY` 也能用：接口返回 `ready:false`，前端降级成手动填菜名，打卡流程不受影响。

### 个人口味画像

`GET /api/preferences/` 从**全部打卡（含私密）**统计：

```json
{ "totalCheckins": 12, "last7Days": 4, "privateCount": 5,
  "topDishes": [{"name":"照烧鸡腿饭","count":3}],
  "topCategories": [{"name":"盖饭","count":4}],
  "topSources": [{"name":"食堂","count":6}] }
```

页面上展示成「我的口味」：总记录 / 近 7 天 / 仅自己可见 + 常吃菜品标签。

## 学籍数据导入

学籍是「谁能注册」的白名单，存在 `users` 表里以**不可登录的占位账号**形式（`username = roster_<学号>`）。
学生注册后走学号核验，通过时占位账号被删除、学号转移到真实账号上。

```bash
cd backend

# 先干跑，确认解析对不对
python manage.py import_students "C:\Users\你\Desktop\计算机学院计金班.csv" --dry-run

# 正式导入（--reset 会先清掉旧占位账号，已绑定的真实账号不受影响）
python manage.py import_students "C:\Users\你\Desktop\计算机学院计金班.csv" --reset
```

CSV 需要表头 `学号,姓名,班级,学院`（列顺序无所谓，按表头取值；编码 UTF-8 / GBK 都能读）。
当前已导入 `计算机学院计金班` 36 人，学院为「计算机学院」。

> 注：`班级` 只用于导入时校验，数据库里没有单独存（核验只比对学号+姓名+学院）。
> 要按班级区分，可以给 `users` 加一列，或把学院写成「计算机学院·计金班」。

## 举报与禁言（治理闭环）

对应文档 2.2.5 / 3.6 节。

**入口**：备餐打卡页，每条别人的打卡右下角有「举报」（自己的内容不显示）。

**流程**：

1. 点「举报」→ 弹出面板，选原因（广告推销 / 违规内容 / 恶意刷屏 / 其他）+ 补充说明
2. 提交后写入 `reports` 表，状态 `pending`；同一条内容同一人只能举报一次
3. 管理员在 `http://127.0.0.1:8000/admin/` 的「举报」里审核，执行「禁言 3 天 / 解禁」
4. 被举报人累计到 **5 次**会自动禁言 24 小时（`AUTO_MUTE_REPORT_COUNT` / `AUTO_MUTE_HOURS`），后台可改

**禁言之后的表现**（三层，前后端都拦）：

| 层 | 表现 |
|---|---|
| 打卡页 | 顶部红色横幅「你当前处于禁言状态，解禁时间 …」 |
| 投票页 | 同样的横幅，且「发起投票」按钮直接禁用 |
| 我的页 | 认证卡片里红色提示「账号已被禁言」+ 解禁时间 |
| 后端 | 所有写接口返回 `403 {"code":"BANNED","message":"…禁言中…"}`，绕过前端也没用 |

**自己演示一遍**（两个账号）：

```bash
python backend/scripts/cleanup_e2e.py     # 清理旧测试账号
cd backend && python manage.py seed       # 恢复 3 条学籍
```

然后用浏览器 A 注册并核验 20230001，发 5 条打卡；浏览器 B 注册并核验 20230002，
逐条举报；B 提交第 5 条时返回 `autoMuted=true`，A 再刷新页面就能看到禁言横幅。

已实测：5 次举报后 A 的 `status=muted`、`ban_until` 为 24 小时后，
A 再发打卡 / 发起投票均返回 403 BANNED。

## 截图

`shots/` 里是真实渲染结果（无头 Chromium 按 1440×960 和 390×844 两个视口截的）：

- `pc-home.png` — 桌面端首页
- `m-home.png` — 手机端首页
- `m-result.png` — 手机端摇出结果
- `m-checkin-post.png` — 手机端发布打卡
- `m-vote-active.png` — 手机端投票达到「过半通过」
- `m-me-verified.png` — 手机端核验通过

## 自检脚本

`scripts/audit.mjs` 通过 CDP 控制真实 Chromium，做两件事：测量两端布局（有没有横向溢出、外壳是否切换）和跑一遍主要交互（摇一摇 → 核验 → 打卡 → 投票过半）。

```bash
# 另开一个终端启动带调试端口的浏览器
msedge --headless --remote-debugging-port=9222 --user-data-dir=%TEMP%\cdp about:blank
# 然后
node scripts/audit.mjs http://127.0.0.1:5180
```

## 目录结构

```
what2eat/
├── server.mjs                  # 零依赖静态服务器（托管 dist + SPA 回退）
├── vite.config.js              # 两套组件库按需引入
├── src/
│   ├── App.vue                 # 只有一处分支：isMobile ? MobileShell : PcShell
│   ├── composables/
│   │   ├── useIsMobile.js      # 断点判断（全局单例）
│   │   └── useToast.js         # 不依赖组件库的轻提示
│   ├── layouts/
│   │   ├── PcShell.vue         # 桌面外壳：el-menu 横向导航
│   │   └── MobileShell.vue     # 手机外壳：van-tabbar 底部导航
│   ├── ui/                     # 跨端控件：同一份页面代码，按端渲染不同组件库
│   │   ├── UButton.vue         # van-button / el-button
│   │   ├── UField.vue          # van-field / el-input
│   │   └── UProgress.vue       # van-progress / el-progress
│   ├── pages/
│   │   ├── Home.vue            # 随机推荐（加权抽样 + 避开近期）
│   │   ├── Checkin.vue         # 备餐打卡
│   │   ├── Vote.vue            # 吃不吃投票（过半规则）
│   │   └── Me.vue              # 身份核验 / 统计 / 收藏
│   ├── data/db.js              # 模拟数据 + 全部业务逻辑（要换成后端就改这里）
│   └── utils/image.js          # 图片压缩
```

关键点：**页面只写一遍**。差异集中在两处——外壳（布局结构完全不同）和 `ui/` 里的三个控件（同一交互，两套组件库实现）。这样既能做出两端的体验差异，又不用维护两份业务逻辑。

## 打包产物也确实是分开的

`pnpm build` 之后看 `dist/assets`：

- `PcShell-*.css` 约 20KB —— Element Plus 的菜单、标签、按钮样式，只在桌面壳里
- `MobileShell-*.css` 约 4KB —— Vant 的 TabBar 样式，只在手机壳里

因为外壳是 `defineAsyncComponent` 懒加载的，手机用户根本不会下载桌面那套 CSS/JS，反之亦然。

## 前后端对接方式

页面不直接碰 HTTP，全部经过 `src/api/`（mock 与真接口二选一，见上文「登录与前后端联调」）。

- **前端部署**：Netlify 静态托管（当前），Cloudflare Pages 为历史方案（见下文部署章节）
- **后端部署**：Railway（Docker + gunicorn + PostgreSQL），代码本身不绑定平台，也支持 SQLite / MySQL、
  WhiteNoise 发静态文件，环境变量与启动命令写在
  [backend/README.md](backend/README.md) 第八节。

切到真后端只需要前端两个环境变量：

```bash
VITE_API_BASE=https://<后端域名>/api
VITE_USE_MOCK=false
```

## 两个必须知道的限制

1. **HTTP 下手机的部分能力不可用**。`capture` 拍照、摇一摇的 `DeviceMotionEvent`、PWA 安装都要求 HTTPS（安全上下文）。局域网 `http://` 地址只能演示界面和按钮流程。Cloudflare Pages 和绝大多数云平台默认给 HTTPS，所以线上不受影响。
2. **演示模式（mock）的数据存在浏览器 localStorage**，换设备/清缓存就没了；切到真后端后数据在服务器数据库里。图片压到 900px 是为了不撑爆 localStorage 的 5MB 配额。

## 当前实际部署（2026-11）

> 下面 Cloudflare Pages 那一节是**历史方案**，当前线上不是这样部署的，保留作参考。

实际形态：

| 部分 | 平台 | 说明 |
| --- | --- | --- |
| 前端 | **Netlify**（直传 `dist` 静态包） | `celebrated-jalebi-812a02.netlify.app` |
| 后端 | **Railway**（Docker + gunicorn） | `what2eat-api-production.up.railway.app` |
| 数据库 | **Railway PostgreSQL** | 容器启动时自动 `migrate` + `bootstrap` 种子数据 |

前端构建命令（本地或 CI 一致）：

```bash
VITE_API_BASE=https://what2eat-api-production.up.railway.app/api \
VITE_USE_MOCK=false \
npx vite build
```

把 `dist/` 打包后拖到 <https://app.netlify.com/drop> 即可更新。**直传包不会自动重建**，前端改动后需要重新打包上传。

Railway 侧的环境变量、启动命令与踩坑记录见 [docs/部署清单-Railway+Neon.md](docs/部署清单-Railway+Neon.md)。

## 部署到 Cloudflare Pages（历史方案，push 自动更新）

纯静态站点，**不需要租服务器**，也不需要买域名。网址形如 `https://<项目名>.pages.dev`。

> **为什么是 Pages 而不是 Workers**：`workers.dev` 的子域是**账号级**的（`<worker>.<账号子域>.workers.dev`），
> 改一次会连带影响账号下所有项目；`pages.dev` 的地址是**项目级**的，每个项目独立，互不干扰。
>
> 也试过 Worker + 静态资源方案，能跑通（`wrangler.jsonc` + `assets.directory` +
> `not_found_handling: single-page-application`），但因为上面这个原因放弃，仓库里的 `wrangler.jsonc` 已删除。

### 步骤

1. 注册 <https://dash.cloudflare.com>（邮箱即可，不用绑卡）。
2. **Workers & Pages** → `Create application`。
3. 关键：新版控制台默认把人往 Worker 流程带（写着 "Configure your **Worker** project" 的那个就是），
   要往下翻，点那行灰色小字 **"Need to use the legacy Pages workflow? → Continue to Pages"**。
   这一步没点对，就会莫名其妙建出一个 Worker。
4. 授权 GitHub（**Only select repositories** 只勾 `what2eat`），选中 `Ares5807/what2eat`。
5. 填配置：
   - Project name：**`what2eatt`**（`what2eat` 已被别人占用；项目名 = 网址，创建后**不能改**）
   - Production branch：`main`
   - Framework preset：**`None`**（预设列表里没有纯 Vite；选 `Vue` 也行，反正下面手填）
   - Build command：`pnpm build`
   - Build output directory：`dist`
   - 环境变量：`NODE_VERSION` = `22`
6. `Save and Deploy`，等 1~2 分钟。
7. 网址 = `https://<项目名>.pages.dev`。

之后每次 push 自动重新部署。

> **坑一**：预设默认会选成 `VitePress`（名字像 Vite），输出目录 `.vitepress/dist`，直接构建失败。
>
> **坑二**：`*.pages.dev` 子域名创建后**无法修改**，改项目名也不会改域名。
> 官方文档原话："`*.pages.dev` subdomains currently cannot be changed. If you need to change your
> `*.pages.dev` subdomain, delete your project and create a new one."

### 关键文件：`public/_redirects`

Pages 靠这个文件做 SPA 回退，否则直接访问 `/vote`、`/me` 会 404：

```
/* /index.html 200
```

> 注意：这行在 **Pages** 里是标准写法；但放到 **Workers** 的静态资源里会报
> `Infinite loop detected in this rule`（Workers 会剥 `.html` 导致自循环）。
> 所以这两个方案不能混用，本项目统一走 Pages。

### 其他已配好的东西

| 文件 | 作用 |
|---|---|
| `package.json` 的 `packageManager` | 云端按 pnpm 11.7.0 构建，避免版本不一致装不上 |
| `vite.config.js` | base 就是 `/`，根路径部署，不用为子路径做任何事 |

### 注意点

| 事项 | 说明 |
|---|---|
| 项目名 | `pages.dev` 子域全球唯一，被占了换一个；**项目名和仓库名可以不一样** |
| 构建失败 | 多半是 Node / pnpm 版本，把日志发我，改环境变量即可 |
| 构建产物 | `dist/` 在 `.gitignore` 里，云端自己构建，不要提交 |
| 私有仓库 | Cloudflare 允许部署私有仓库，不必公开 |
| 想要 `www.xxx.com` | 买个域名（`.top` 首年十几块），项目设置里 Add custom domain，自动签发 HTTPS。答辩不必买 |

### 备选：Vercel

`vercel.json` 还留着。注册 <https://vercel.com> 导入仓库即可，网址 `xxx.vercel.app`，同样是项目级、互不影响。不想用直接删这个文件。

> 建议两个都挂上（各 5 分钟）：国内访问 `pages.dev` 和 `vercel.app` 都不算稳，答辩当天哪个能打开用哪个。

### 一个必须知道的边界

Cloudflare / Vercel 只托管**静态文件，跑不了 Python**。所以前端放它们那儿，后端要单独部署一台能跑 Python 进程的服务（云服务器、容器平台、PaaS 都行），再把地址配成前端的 `VITE_API_BASE`。具体要填哪些环境变量、怎么启动，见 [backend/README.md](backend/README.md) 第八节。

## 自己改代码

```bash
pnpm install
pnpm dev      # http://localhost:5180，热更新
pnpm build && node server.mjs
```

日常流程跟你的同学一样：改代码 → GitHub Desktop 里 Commit → Push → 等 1 分钟 → 刷新网址。本地 `pnpm dev` 用来即时预览，两者互不干扰。

> 本机 `pnpm dev` 若报 `spawn EPERM`，说明当前终端有沙箱限制，换一个普通终端运行即可。
