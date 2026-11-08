import { computed, reactive } from 'vue'
import * as api from '@/api'
import { usingMock } from '@/api'
import { state as mockState } from '@/data/db'

/**
 * 应用级状态。
 *
 * 设计原则：页面只跟这里打交道，不直接碰 `@/data/db`，也不直接调 `@/api`。
 * - mock 模式：读 db.js 的本地数据（线上演示站就是这种）
 * - 真接口模式：调 Django，把结果放进同一个 ui 对象
 *
 * 页面因此不用关心底座是 mock 还是 HTTP，只等 await 就行。
 */

const USER_KEY = 'what2eat:user'
const EATEN_KEY = 'what2eat:eaten'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

function readEaten() {
  try {
    const raw = JSON.parse(localStorage.getItem(EATEN_KEY) || '[]')
    return Array.isArray(raw) ? raw.slice(0, 12) : []
  } catch {
    return []
  }
}

export const ui = reactive({
  user: readUser(),
  checkins: [],
  votes: [],
  favorites: {}, // { dishId: true } —— 模板里用 Object.keys(...).length
  favoriteList: [], // 收藏的菜品对象，页面直接渲染
  likes: {},
  eaten: readEaten(), // 「最近抽到」的本地环，纯 UI 状态
  preferences: null, // 个人饮食偏好画像
  loading: false,
})

export const isLoggedIn = computed(() =>
  Boolean(ui.user?.username || ui.user?.studentId || ui.user?.studentId === 0),
)

export const isVerified = computed(() => Boolean(ui.user?.verified))

export const displayName = computed(
  () => ui.user?.name || ui.user?.username || (usingMock ? '同学' : '未登录'),
)

/** 是否处于禁言 / 封禁状态，页面据此禁用发布并提示 */
export const isMuted = computed(
  () => Boolean(ui.user?.banned || ui.user?.muted || ['muted', 'banned'].includes(ui.user?.status)),
)

/** 禁言到期时间，展示用 */
export const mutedUntilText = computed(() => {
  const raw = ui.user?.banUntil
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
})

function persistUser(user) {
  ui.user = user
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(USER_KEY)
  } catch {
    /* 无痕模式下写不进去，不影响使用 */
  }
}

/** 把后端 / mock 返回的用户对象归一化成页面认识的样子 */
export function normalizeUser(raw) {
  if (!raw) return null
  const studentId = raw.studentId || raw.student_id || ''
  const status = raw.status || 'normal'
  return {
    id: raw.id ?? null,
    username: raw.username || studentId || '',
    name: raw.name || '',
    studentId,
    college: raw.college || '',
    // 后端有 verified 字段；mock 的 db.state.user 只有 verified 布尔
    verified: Boolean(raw.verified ?? studentId),
    role: raw.role || 'student',
    status,
    // 禁言 / 封禁状态（后端 UserProfileSerializer 直接给 muted / banned）
    muted: Boolean(raw.muted ?? status === 'muted'),
    banned: Boolean(raw.banned ?? status === 'banned'),
    banUntil: raw.ban_until || raw.banUntil || '',
    reportCount: raw.report_count ?? raw.reportCount ?? 0,
  }
}

/** mock 模式下，db.js 才是用户状态的源头，启动时对齐一次 */
if (usingMock) {
  const m = mockState.user
  if (m && (m.verified || m.name)) persistUser(normalizeUser(m))
}

// ---------------------------------------------------------------------------
// 认证
// ---------------------------------------------------------------------------

export async function login({ username, password }) {
  const res = await api.login({ username, password })
  if (res.ok) persistUser(normalizeUser(res.user) || { username, verified: false })
  return res
}

export async function register(form) {
  const res = await api.register(form)
  if (res.ok) persistUser(normalizeUser(res.user) || { username: form.username, verified: false })
  return res
}

export async function bindStudent(form) {
  const res = await api.verifyStudent(form)
  if (res.ok) {
    persistUser(normalizeUser(res.user) || { ...form, verified: true })
  }
  return res
}

export async function logout() {
  await api.logout()
  persistUser(null)
  ui.checkins = []
  ui.votes = []
  ui.favorites = {}
  ui.favoriteList = []
  ui.likes = {}
  ui.eaten = []
  try {
    localStorage.removeItem(EATEN_KEY)
  } catch {
    /* ignore */
  }
}

// ---------------------------------------------------------------------------
// 列表
// ---------------------------------------------------------------------------

export async function loadCheckins(scope) {
  ui.loading = true
  try {
    ui.checkins = await api.listCheckins(scope)
  } finally {
    ui.loading = false
  }
  return ui.checkins
}

/** 个人偏好画像：来自全部打卡（含私密），所以不加入社区也能攒出来 */
export async function loadPreferences() {
  if (!isLoggedIn.value) {
    ui.preferences = null
    return null
  }
  try {
    ui.preferences = await api.loadPreferences()
  } catch {
    ui.preferences = null
  }
  return ui.preferences
}

export async function loadVotes() {
  ui.loading = true
  try {
    ui.votes = await api.listVotes()
  } finally {
    ui.loading = false
  }
  return ui.votes
}

export async function loadFavorites() {
  const list = await api.favoriteDishes()
  const map = {}
  for (const d of list || []) map[d.id] = true
  ui.favorites = map
  ui.favoriteList = list || []
  return list || []
}

// ---------------------------------------------------------------------------
// 抽签历史（纯本地）
// ---------------------------------------------------------------------------

export function pushEaten(dish) {
  if (!dish?.id) return
  const item = {
    id: dish.id,
    dishId: dish.id,
    name: dish.name,
    emoji: dish.emoji || '🍽️',
    price: dish.price,
  }
  ui.eaten = [item, ...ui.eaten.filter((e) => e.id !== dish.id)].slice(0, 12)
  try {
    localStorage.setItem(EATEN_KEY, JSON.stringify(ui.eaten))
  } catch {
    /* ignore */
  }
}

export function eatenDishIds() {
  return ui.eaten.map((e) => e.dishId)
}
