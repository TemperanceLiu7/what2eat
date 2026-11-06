# 校园「今天吃什么」· 同址多端演示版

一个**网址**，同时给电脑和手机用：宽屏进来是 Element Plus 的桌面布局（顶部导航 + 左右分栏），窄屏或手机进来是 Vant 的移动布局（底部 TabBar + 单列卡片）。后端接口用本地模拟数据顶替，不需要启动 Django 就能完整演示。

## 已经能跑的地址

- 电脑：<http://localhost:5180>
- 手机：`http://10.6.60.42:5180`（手机和电脑连同一个 Wi-Fi）

> 服务是用 `server.mjs` 托管 `dist/` 的，纯静态、零依赖。想换端口：`PORT=8080 node server.mjs`。

## 怎么验证「同一个网址，两套界面」

1. 电脑浏览器打开 <http://localhost:5180>，看到的是顶部横向导航 + 左推荐右人气榜。
2. 把窗口拖窄到 820px 以下（或者按 F12 → 切换设备工具栏选 iPhone），**不刷新**，会实时切成手机布局：头部变矮、底部出现 TabBar、卡片变单列。
3. 手机扫码/输入上面那个局域网地址，打开的是同一个 URL、同一份代码。

切换逻辑在 `src/composables/useIsMobile.js`，用 `matchMedia('(max-width: 820px)')`，不是 UA 判断——所以 iPad 分屏、旋转屏幕都能正确响应，分享出去的链接也永远自适配当前设备。

## 演示流程（建议按这个顺序走）

1. **我的** → 点「填入演示账号」→ 提交核验（学号 20230001 / 张同学 / 计算机学院）。
   这一步是为了让你看到「未认证不能发布」的拦截效果，可以先不认证直接去打卡试试。
2. **随机推荐** → 选范围（食堂/外卖/饭店/夜市）→ 摇一摇。
   手机上第一次点按钮会申请动作权限，授权后可以直接甩手机抽签。
3. 抽到结果后点 👍 收藏 / ❤️ 点赞，热度会进入下一轮的加权随机。
4. **备餐打卡** → 拍照或选图 → 写两句 → 发布（会压成 900px 的 JPEG 存本地）。
5. **吃不吃投票** → 发起投票（默认 6 人，过半需 4 票）→ 自己投一票 → 点「模拟同学」看票数推进到「通过」或「未通过」。

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

## 换成真后端（Django + DRF）

`src/data/db.js` 里每个导出函数都刻意写成了「异步 + `{ ok, message }`」的形状，替换时只改函数体：

```js
// 例：把本地收藏换成接口
export async function toggleFavorite(id) {
  const { data } = await axios.post('/api/favorites/toggle/', { dish_id: id })
  state.favorites[id] = data.favorited
  return data
}
```

页面里的 `await`、错误提示、`ok` 判断全都不用动。建议顺序：

1. `DISHES` / `SHOPS` 换成 `GET /api/dishes/`；
2. `pickRandom` 换成 `GET /api/dishes/random/?source=canteen`（权重抽样放后端，别在前端算，否则数据量大了一个都抽不准）；
3. `verifyStudent` 换成 `POST /api/auth/bind-student/`，核验逻辑必须在服务端；
4. 打卡图片的 base64 换成 `POST /api/upload/` 拿 URL。

## 两个必须知道的限制

1. **HTTP 下手机的部分能力不可用**。`capture` 拍照、摇一摇的 `DeviceMotionEvent`、PWA 安装都要求 HTTPS（安全上下文）。局域网 `http://` 地址只能演示界面和按钮流程。正式演示建议用 Cloudflare Tunnel 或 Caddy 自动证书挂个域名，二维码一次搞定。
2. **数据存在浏览器 localStorage**，换设备/清缓存就没了。图片压到 900px 是为了不撑爆 5MB 配额，存十几条打卡没问题。

## 部署到 Cloudflare Workers（改本地 → push → 网址自动更新）

纯静态站点，**不需要租服务器**，也不需要买域名。网址形如 `https://what2eat.<你的子域>.workers.dev`。

> 为什么用 Workers 而不是 Pages：`pages.dev` 的好名字基本被占完了，而 Worker 名字只在自己账号下唯一，随便起。

### 步骤

1. 注册 <https://dash.cloudflare.com>（邮箱即可，不用绑卡）。
2. **Workers & Pages** → `Create` → `Import a repository` → 授权 GitHub、选中 `what2eat` 仓库。
3. 填配置：
   - Project name：`what2eat`（**必须和 `wrangler.jsonc` 里的 `name` 一致**）
   - Production branch：`main`
   - Build command：`pnpm build`
   - Deploy command：`npx wrangler deploy`（默认值，别改）
   - 环境变量：`NODE_VERSION` = `22`
4. `Deploy`，等 1~2 分钟。
5. 网址：`https://what2eat.<你的子域>.workers.dev`（子域在 Workers & Pages 首页能看到）。

之后每次 push 自动重新部署。

### 关键文件：`wrangler.jsonc`

Worker 本身是个跑 JS 的东西，它不知道怎么发静态文件，必须靠这份配置告诉它：

```jsonc
{
  "name": "what2eat",              // 必须等于 Cloudflare 上的项目名
  "compatibility_date": "2025-06-01",
  "assets": {
    "directory": "./dist",          // Vite 的构建产物
    "not_found_handling": "single-page-application"   // 深链接回退到 index.html
  }
}
```

少了 `assets` 会报 `Missing entry-point to Worker script or to assets directory`；少了 `not_found_handling`，直接访问 `/vote` 会 404。

### 其他已配好的东西

| 文件 | 作用 |
|---|---|
| `package.json` 的 `packageManager` | 云端按 pnpm 11.7.0 构建，避免版本不一致装不上 |
| `vite.config.js` | base 就是 `/`，根路径部署，不用为子路径做任何事 |

> 注意：**不要**再放 `_redirects`。`/* /index.html 200` 会和 `not_found_handling: single-page-application` 冲突，
> 部署时直接报 `Infinite loop detected in this rule`。SPA 回退只保留 `wrangler.jsonc` 里那一处就够了。

### 注意点

| 事项 | 说明 |
|---|---|
| 项目名 | Worker 名只在本账号内唯一，重名也没关系；网址里的 `<子域>` 由账号决定 |
| 构建失败 | 多半是 Node / pnpm 版本，把日志发我，改环境变量即可 |
| 构建产物 | `dist/` 在 `.gitignore` 里，云端自己构建，不要提交 |
| 私有仓库 | Cloudflare 允许部署私有仓库，不必公开 |
| 想要 `www.xxx.com` | 买个域名（`.top` 首年十几块），项目设置里 Add custom domain，自动签发 HTTPS。答辩不必买 |

### 备选：Vercel

`vercel.json` 还留着。注册 <https://vercel.com> 导入仓库即可，网址 `xxx.vercel.app`。不想用直接删这个文件，不影响 Cloudflare。

> 建议两个都挂上（各 5 分钟）：国内访问 `workers.dev` 和 `vercel.app` 都不算稳，答辩当天哪个能打开用哪个。

### 一个必须知道的边界

Cloudflare / Vercel 只托管**静态文件，跑不了 Python**。等你接 Django 后端时，前端继续放这里，后端要另外部署（Railway、Render、PythonAnywhere 都有免费额度），再把接口地址配成环境变量。现在这版没有后端，完全够用。

## 自己改代码

```bash
pnpm install
pnpm dev      # http://localhost:5180，热更新
pnpm build && node server.mjs
```

日常流程跟你的同学一样：改代码 → GitHub Desktop 里 Commit → Push → 等 1 分钟 → 刷新网址。本地 `pnpm dev` 用来即时预览，两者互不干扰。

> 本机 `pnpm dev` 若报 `spawn EPERM`，说明当前终端有沙箱限制，换一个普通终端运行即可。
