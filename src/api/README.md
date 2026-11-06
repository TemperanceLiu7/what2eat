# `src/api/` —— 接口契约层

页面以后不直接碰 `db.js`，统一从这里拿数据。当前默认走 **mock**（数据还是 `db.js` 那套 localStorage 演示数据），
Django 后端好了之后改一个环境变量就切过去，页面代码不用动。

```
src/api/
├── client.js   # fetch 封装：baseURL / 超时 / JSON / Bearer 鉴权 / 统一解析 / ApiError
├── errors.js   # 错误码 → 中文提示，messageOf(err)
├── index.js    # 契约函数（唯一入口），按环境变量选 mock 还是真接口
├── mock.js     # mock 适配器，转调 db.js 里的同名实现
└── README.md   # 本文件
```

## 一、切真后端

在项目根目录新建 `.env.local`：

```dotenv
# Django 地址；末尾斜杠会自动去掉，不写就退回同源 /api（走 vite 代理或 nginx）
VITE_API_BASE=http://127.0.0.1:8000/api
# 关键开关：不写或写 true 都是 mock，只有字面量 false 才发真实请求
VITE_USE_MOCK=false
```

改完 **重启 `pnpm dev`**（Vite 的环境变量是启动时注入的），`pnpm build` 同样生效。

> `.gitignore` 里目前没有 `.env.local`，本地联调完记得别把它提交上去（本次没有改动任何已有文件）。

## 二、接口清单

所有函数都返回 `Promise`。路径相对 `VITE_API_BASE`。

| 前端函数 | 方法 & 路径 | 入参 → body / query |
| --- | --- | --- |
| `verifyStudent({ studentId, name, college })` | `POST /auth/bind-student/` | `{ student_id, name, college }` |
| `pickRandom(source)` | `GET /dishes/random/?source=` | `source` 取 `all/canteen/takeout/restaurant/night` |
| `toggleLike(targetType, targetId)` | `POST /likes/toggle/` | `{ target_type, target_id }` |
| `toggleFavorite(targetType, targetId)` | `POST /favorites/toggle/` | `{ target_type, target_id }` |
| `favoriteDishes()` | `GET /favorites/` | — |
| `addCheckin({ content, image, dishName })` | `POST /checkins/` | `{ content, image, dish_name }` |
| `createVote({ title, target, targetCount })` | `POST /votes/` | `{ title, target, target_count }` |
| `castVote(voteId, option)` | `POST /votes/{id}/cast/` | `{ option: 'agree' \| 'disagree' }` |
| `login({ username, password })` | `POST /auth/token/` | `{ username, password }` |
| `register({ username, password, ... })` | `POST /auth/register/` | 其余字段原样透传 |

统一响应信封（`client.js` 负责解析，`code` 为业务码，成功时可以是 `0`）：

```json
{ "ok": true, "data": { "...": "..." }, "message": "核验通过", "code": 0 }
```

### 示例

**核验学号**

```http
POST /api/auth/bind-student/
{ "student_id": "20230001", "name": "张同学", "college": "计算机学院" }

→ 200
{ "ok": true, "message": "核验通过",
  "data": { "token": "eyJhb...", "user": { "studentId": "20230001", "name": "张同学", "college": "计算机学院", "verified": true } } }
```

```js
const res = await verifyStudent({ studentId: '20230001', name: '张同学', college: '计算机学院' })
if (!res.ok) toast(res.message) // 失败时看 message；真接口还会带 res.code（UNVERIFIED / INVALID_DATA 之类）
// token 已自动写入 localStorage['what2eat:token']
```

**抽一道菜**：`GET /api/dishes/random/?source=canteen`

```json
{ "ok": true, "data": { "dish": { "id": "d1", "name": "鱼香肉丝盖饭", "price": 12, "likes": 36, "favorites": 12, "shopId": "s1" } } }
```

```js
const dish = await pickRandom('canteen') // 返回菜品对象；这个来源没菜时返回 null
```

**点赞 / 收藏**：`POST /api/likes/toggle/` 与 `POST /api/favorites/toggle/`

```json
// 请求
{ "target_type": "dish", "target_id": "d1" }
// 响应
{ "ok": true, "data": { "liked": true, "likes": 37 } }
```

```js
const on = await toggleLike('dish', 'd1') // true = 点上了，false = 取消了
const list = await favoriteDishes() // [{ id, name, ... }]，失败会抛 ApiError
```

**发打卡**：`POST /api/checkins/`

```json
{ "content": "三食堂牛肉面，加了个蛋", "image": "data:image/jpeg;base64,...", "dish_name": "牛肉拉面" }
→ { "ok": true, "message": "打卡成功", "data": { "checkin": { "id": "c1", "at": 1710000000000 } } }
```

**发起投票 / 投票**：`POST /api/votes/`、`POST /api/votes/v1/cast/`

```json
// 发起
{ "title": "今晚去不去西门鸡公煲", "target": "西门鸡公煲", "target_count": 6 }
→ { "ok": true, "message": "投票已创建", "data": { "vote": { "id": "v1", "agree": 0, "disagree": 0, "status": "ongoing" } } }

// 投票
{ "option": "agree" }
→ { "ok": true, "message": "投票成功" }
```

```js
const { ok, vote } = await createVote({ title: '今晚去吃啥', target: '西门', targetCount: 6 })
const r = await castVote('v1', 'agree')
if (!r.ok) toast(r.message) // 已投过 = ALREADY_VOTED，结束了 = VOTE_CLOSED
```

**登录 / 注册**（`login` / `register` 在 `db.js` 里没有对应实现，是这次按契约补的）

```json
POST /api/auth/token/   { "username": "20230001", "password": "******" }
→ { "ok": true, "data": { "token": "eyJhb...", "user": { "id": 1, "name": "张同学" } } }
```

```js
const { ok, message } = await login({ username: '20230001', password: '******' })
await register({ username: '20230002', password: '******', name: '李同学', studentId: '20230002', college: '外国语学院' })
```

## 三、错误处理

`client.js` 失败一律抛 `ApiError`，三个字段：`status`（HTTP 状态码，`0` 表示没发出去）、`code`（业务码）、`message`（中文文案），
外加一个 `data`（后端返回的原始 `data`，需要细节时用）。

```js
import { ApiError } from '@/api'

try {
  const list = await favoriteDishes()
} catch (err) {
  if (err instanceof ApiError) {
    if (err.status === 401) router.push('/login')
    toast(err.message)
  }
}
```

`verifyStudent / addCheckin / createVote / castVote / login / register` 这 6 个和 `db.js` 的风格一致，
**不抛错**，失败返回 `{ ok: false, message, code }`，页面 `if (!res.ok)` 就行（`login / register` 是这次新增的，
`db.js` 里没有，但返回形状同样如此）；其余几个失败会抛 `ApiError`，需要 `try/catch`。
`pickRandom` 比较特殊：这个来源没有菜时（后端 404）返回 `null`，对页面就是「没抽到」，其余失败仍然抛错。

### 错误码表

| `code` | 常见状态码 | 场景 | 默认提示 |
| --- | --- | --- | --- |
| `UNVERIFIED` | 403 | 没做学号核验就发打卡 / 投票 | 请先完成学号核验 |
| `BANNED` | 403 | 账号被封禁 | 该账号已被封禁，无法操作 |
| `ALREADY_VOTED` | 409 | 同一人重复投票 | 你已经投过票了，每人只能投一次 |
| `VOTE_CLOSED` | 409 / 410 | 投票已结束或已截止 | 投票已结束，不能再投 |
| `INVALID_DATA` | 400 | 参数缺失 / 格式不对 | 提交的数据不合法，请检查后重试 |
| `TIMEOUT` | 0 | 超过 10s 被 `AbortController` 掐断 | 请求超时，请检查网络后重试 |
| `NETWORK` | 0 | 断网、DNS 挂了、跨域被拦 | 网络连接失败，请稍后重试 |
| `UNAUTHORIZED` | 401 | token 没了 / 过期 | 登录状态已失效，请重新登录 |
| `FORBIDDEN` | 403 | 有登录态但没权限 | 没有权限执行这个操作 |
| `NOT_FOUND` | 404 | 资源不存在 | 请求的内容不存在 |
| `TOO_MANY_REQUESTS` | 429 | 触发限流 | 操作太频繁，歇一会儿再试 |
| `SERVER_ERROR` | 500 / 502 / 503 | 后端或代理挂了 | 服务器开小差了，请稍后再试 |
| `BAD_RESPONSE` | 任意 | 返回的不是 JSON（多半是代理错误页） | 服务器返回了异常内容，请稍后再试 |

取文案：`import { messageOf } from '@/api'` → `messageOf(err)`；后端在 `message` 里给了中文就以它为准，
否则按 `code` → 状态码 → 兜底 的顺序翻译。加新错误码只改 `errors.js` 一张表。

## 四、后端还没好时怎么开发

1. `.env.local` 里**不写** `VITE_USE_MOCK`（或写 `VITE_USE_MOCK=true`），`pnpm dev` 起来照常用。
2. 所有函数转调 `db.js`，数据存在 `localStorage['what2eat:v1']`；要清空走「我的 → 清空演示数据」。
3. mock 演示账号：学号 `20230001`，密码 `123456`（登录后会自动完成核验）。
4. mock 与真接口的差异（只有这些，且都在 `mock.js` 里消化掉了）：
   - 全部返回 `Promise`，所以页面统一按异步写，切后端时不用改；
   - `login / register` 是本地假实现，不校验学号唯一性、不发真 token；
   - `toggleLike / toggleFavorite` 兼容旧写法 `toggleLike('d1')` 和新写法 `toggleLike('dish', 'd1')`；
   - mock 不发 HTTP，也不做超时，接口错误由 `db.js` 自己返回 `{ ok: false, message }`（核验那几条还会带 `code`）。
5. 想验证真接口但后端只做了一半？新建一个临时 `.env.local`，`VITE_API_BASE` 指向
   `http://127.0.0.1:8000/api` 并设 `VITE_USE_MOCK=false` 就能单独试某几个接口；跨域被拦的话，
   在 `vite.config.js` 的 `server` 里加 `proxy: { '/api': 'http://127.0.0.1:8000' }`（本次不动已有文件，留给你加），
   或者直接 `curl` 上面的路径对字段。

## 五、页面迁移步骤

```js
// 之前
import { pickRandom, toggleLike } from '@/data/db'
const dish = pickRandom('all')
const on = toggleLike(dish.id)

// 之后
import { pickRandom, toggleLike } from '@/api'
const dish = await pickRandom('all')
const on = await toggleLike('dish', dish.id)
```

只是 `db.js` 的**非接口**内容（`state`、`isLiked`、`fmtTime`、`SOURCES` 这类纯本地/纯展示的）不用搬，
仍然从 `@/data/db` 取；等数据层整体搬到后端时再一起处理。本次没有改动任何页面，所以现在的 UI 行为完全不变。
