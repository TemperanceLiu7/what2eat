import { ApiError, clearToken, get, post, setToken } from './client'
import { messageOf } from './errors'
import * as mock from './mock'

/**
 * 接口契约层。
 * 函数名、入参、返回形状都对着 src/data/db.js 抄，页面以后只要把
 * import 从 '@/data/db' 换成 '@/api'，调用处补个 await 就完事：
 *
 *   const dish = await pickRandom('canteen')
 *
 * 切真后端只改环境变量（.env.local）：
 *   VITE_API_BASE=https://api.example.com/api
 *   VITE_USE_MOCK=false
 */

// 和 client.js 一样做个 env 兜底，脱离 Vite 环境时不至于在 import 阶段就报错
const env = import.meta.env || {}

/** 默认走 mock；只有显式写 VITE_USE_MOCK=false 才打真接口 */
export const usingMock = env.VITE_USE_MOCK !== 'false'

/**
 * 契约里「返回 { ok, message }」的那批接口（核验 / 打卡 / 投票）：
 * 失败不向外抛，转成 { ok:false, message, code } 返回，
 * 页面里的 `if (!res.ok) toast(res.message)` 照旧能用。
 */
async function asResult(task, extra) {
  try {
    const res = await task()
    return { ok: true, message: res.message || '操作成功', ...(extra ? extra(res) : {}) }
  } catch (err) {
    return {
      ok: false,
      message: messageOf(err),
      code: err instanceof ApiError ? err.code : 'UNKNOWN',
    }
  }
}

// ---------------------------------------------------------------------------
// 真实接口实现（Django / DRF）
// ---------------------------------------------------------------------------

const http = {
  // 学号 + 姓名 + 学院 三重核验，成功后端直接下发登录态
  verifyStudent({ studentId, name, college } = {}) {
    return asResult(
      () => post('/auth/bind-student/', { student_id: studentId, name, college }),
      (res) => {
        if (res.data?.token) setToken(res.data.token)
        return { user: res.data?.user || null }
      },
    )
  },

  login({ username, password } = {}) {
    return asResult(
      () => post('/auth/token/', { username, password }, { auth: false }),
      (res) => {
        const token = res.data?.token || res.data?.access || ''
        if (!token) throw new ApiError('登录失败：服务端没有返回 token', { code: 'BAD_RESPONSE' })
        setToken(token)
        return { token, user: res.data?.user || null }
      },
    )
  },

  register({ username, password, ...rest } = {}) {
    return asResult(
      () => post('/auth/register/', { username, password, ...rest }, { auth: false }),
      (res) => {
        // 有的后端注册完直接给 token，有的要再登一次，两种都兼容
        const token = res.data?.token || res.data?.access || ''
        if (token) setToken(token)
        return { token, user: res.data?.user || null }
      },
    )
  },

  // 该来源下没有菜时后端可能回 404，对页面来说就是「没抽到」，返回 null 更顺手
  async pickRandom(source = 'all') {
    try {
      const res = await get('/dishes/random/', { source })
      return res.data?.dish || res.data || null
    } catch (err) {
      if (err?.status === 404) return null
      throw err
    }
  },

  async toggleLike(targetType, targetId) {
    const res = await post('/likes/toggle/', { target_type: targetType, target_id: targetId })
    return Boolean(res.data?.liked ?? res.data?.on ?? res.data)
  },

  async toggleFavorite(targetType, targetId) {
    const res = await post('/favorites/toggle/', { target_type: targetType, target_id: targetId })
    return Boolean(res.data?.favorited ?? res.data?.on ?? res.data)
  },

  async favoriteDishes() {
    const res = await get('/favorites/')
    const list = res.data?.items || res.data
    return Array.isArray(list) ? list : []
  },

  addCheckin({ content, image, dishName, visibility } = {}) {
    return asResult(() =>
      post('/checkins/', { content, image, dish_name: dishName, visibility }),
    )
  },

  createVote({ title, target, targetCount } = {}) {
    return asResult(
      () => post('/votes/', { title, target, target_count: targetCount }),
      (res) => ({ vote: res.data?.vote || res.data || null }),
    )
  },

  castVote(voteId, option) {
    return asResult(() => post(`/votes/${encodeURIComponent(voteId)}/cast/`, { option }))
  },

  requestReview(voteId) {
    return asResult(
      () => post(`/votes/${encodeURIComponent(voteId)}/review/`),
      (res) => ({
        vote: res.data?.vote || null,
        targetCount: res.data?.targetCount ?? null,
      }),
    )
  },

  async listCheckins(scope) {
    const res = await get('/checkins/', scope === 'mine' ? { scope: 'mine' } : {})
    const list = res.data?.items || res.data
    return Array.isArray(list) ? list : []
  },

  async recognizeImage(image) {
    const res = await post('/recognize/', { image }, { timeout: 60000 })
    return {
      dishes: res.data?.dishes || [],
      note: res.data?.note || '',
      ready: res.data?.ready !== false,
    }
  },

  async loadPreferences() {
    const res = await get('/preferences/')
    return res.data || {}
  },

  async listVotes() {
    const res = await get('/votes/')
    const list = res.data?.items || res.data
    return Array.isArray(list) ? list : []
  },

  // 「模拟同学投票」是演示版专有的，真接口下没有这个能力
  async simulateVotes() {
    return { ok: false, message: '真接口模式下没有「模拟同学投票」', count: 0 }
  },

  async logout() {
    clearToken()
    return { ok: true, message: '已退出登录' }
  },

  report({ reportedId, targetType, targetId, reason } = {}) {    return asResult(
      () =>
        post('/reports/', {
          reported_id: reportedId,
          target_type: targetType,
          target_id: targetId,
          reason,
        }),
      (res) => ({
        reportCount: res.data?.reportCount ?? 0,
        autoMuted: Boolean(res.data?.autoMuted),
      }),
    )
  },
}

// ---------------------------------------------------------------------------
// 对外导出：签名和 db.js 保持一致，调用方感知不到底下是 mock 还是真接口
// ---------------------------------------------------------------------------

const impl = usingMock ? mock : http

export const verifyStudent = (params) => impl.verifyStudent(params)
export const login = (params) => impl.login(params)
export const register = (params) => impl.register(params)
export const pickRandom = (source) => impl.pickRandom(source)
export const toggleLike = (targetType, targetId) => impl.toggleLike(targetType, targetId)
export const toggleFavorite = (targetType, targetId) => impl.toggleFavorite(targetType, targetId)
export const favoriteDishes = () => impl.favoriteDishes()
export const addCheckin = (params) => impl.addCheckin(params)
export const createVote = (params) => impl.createVote(params)
export const castVote = (voteId, option) => impl.castVote(voteId, option)
export const requestReview = (voteId) => impl.requestReview(voteId)
export const listCheckins = (scope) => impl.listCheckins(scope)
export const recognizeImage = (image) => impl.recognizeImage(image)
export const loadPreferences = () => impl.loadPreferences()
export const listVotes = () => impl.listVotes()
export const simulateVotes = (voteId, count) => impl.simulateVotes(voteId, count)
export const logout = () => impl.logout()
export const report = (params) => impl.report(params)

// 页面想主动处理错误（比如 401 跳登录）时用得上
export { ApiError, messageOf }
