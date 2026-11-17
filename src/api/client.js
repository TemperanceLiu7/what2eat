import { ERROR_MESSAGES, codeOfStatus } from './errors'

/**
 * 契约层 HTTP 客户端：只用原生 fetch，不引第三方库。
 * 负责 baseURL 拼接、JSON 序列化、超时、Bearer 鉴权，并把后端统一的
 * { ok, data, message, code } 解析成信封返回；任何失败都抛 ApiError，
 * 页面只需要 catch 一种错误。
 */

const TOKEN_KEY = 'what2eat:token'
// 免费托管（Render Free）会休眠，首个请求要等实例冷启动，10s 容易直接超时
const DEFAULT_TIMEOUT = 20 * 1000

// 取一层 env 兜底：正常在 Vite 里跑一定有值，脱离 Vite（比如单测）时也不会在 import 阶段炸掉
const env = import.meta.env || {}

/** 真后端地址；没配就走同源 /api（vite 代理或 nginx 转发到 Django） */
const BASE_URL = String(env.VITE_API_BASE || '/api').replace(/\/+$/, '')

/** 统一错误类型：status / code / message 三件套，够页面做提示和分支了 */
export class ApiError extends Error {
  /**
   * @param {string} message 给人看的中文提示
   * @param {{ status?: number, code?: string, data?: any }} [extra]
   *   status = 0 表示请求没发出去（断网 / 超时）
   */
  constructor(message, extra = {}) {
    super(message || ERROR_MESSAGES.UNKNOWN)
    this.name = 'ApiError'
    this.status = extra.status || 0
    // 没给业务码就按状态码推一个，别让 UNKNOWN 把 401/500 的提示盖掉
    this.code = extra.code || codeOfStatus(this.status)
    this.data = extra.data ?? null
  }
}

const isApiError = (err) => err instanceof ApiError || err?.name === 'ApiError'

// ---------------------------------------------------------------------------
// token：存在 localStorage，刷新页面不掉登录态
// ---------------------------------------------------------------------------

function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

/** 传空值等于清空，方便登录失效时统一处理 */
export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* 无痕模式下写不进去，当次会话仍然可用 */
  }
}

export function clearToken() {
  setToken('')
}

// ---------------------------------------------------------------------------
// 请求
// ---------------------------------------------------------------------------

function buildUrl(path, params) {
  const p = String(path || '')
  let url = /^https?:\/\//i.test(p) ? p : `${BASE_URL}${p.startsWith('/') ? '' : '/'}${p}`

  const search = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.append(key, value)
  })
  const qs = search.toString()
  if (qs) url += (url.includes('?') ? '&' : '?') + qs
  return url
}

/** 后端可能返回裸数据（比如代理层塞的 JSON），这里统一成信封 */
function normalize(payload, status) {
  if (payload && typeof payload === 'object' && typeof payload.ok === 'boolean') {
    return {
      ok: payload.ok,
      data: payload.data ?? null,
      message: payload.message || '',
      code: payload.code ?? null,
    }
  }
  return { ok: status >= 200 && status < 300, data: payload ?? null, message: '', code: null }
}

/**
 * 发一个请求，成功 resolve 信封 { ok, data, message, code }，失败 reject ApiError。
 * @param {string} path 相对 BASE_URL 的路径，如 '/votes/1/cast/'
 * @param {{ method?: string, body?: any, params?: object, headers?: object, timeout?: number, auth?: boolean }} [options]
 */
async function request(path, options = {}) {
  const { method = 'GET', body, params, headers, timeout = DEFAULT_TIMEOUT, auth = true } = options

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  const finalHeaders = { Accept: 'application/json', ...(headers || {}) }
  const init = { method, headers: finalHeaders, signal: controller.signal }

  if (body !== undefined) {
    finalHeaders['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }

  const token = auth ? getToken() : ''
  if (token) finalHeaders.Authorization = `Bearer ${token}`

  try {
    const res = await fetch(buildUrl(path, params), init)
    const text = await res.text().catch(() => '')

    let payload = null
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        // 代理挂了会返回 HTML，这时不能指望能解析
        throw new ApiError(ERROR_MESSAGES.BAD_RESPONSE, { status: res.status, code: 'BAD_RESPONSE' })
      }
    }

    const env = normalize(payload, res.status)

    // 状态码和业务 ok 任一说失败就算失败，宁可多报错也不要假装成功
    if (!res.ok || !env.ok) {
      const code = env.code || codeOfStatus(res.status)
      throw new ApiError(env.message || ERROR_MESSAGES[code] || ERROR_MESSAGES.UNKNOWN, {
        status: res.status,
        code,
        data: env.data,
      })
    }

    return env
  } catch (err) {
    if (isApiError(err)) throw err
    if (err?.name === 'AbortError') throw new ApiError(ERROR_MESSAGES.TIMEOUT, { code: 'TIMEOUT' })
    throw new ApiError(ERROR_MESSAGES.NETWORK, { code: 'NETWORK' })
  } finally {
    clearTimeout(timer)
  }
}

/**
 * 预热：真接口模式下页面一打开就悄悄打一次 /health/。
 * 免费托管 15 分钟无流量会休眠，冷启动约 30 秒——提前叫醒，
 * 等用户真正点「抽一道」时实例已经起来了。
 */
export function warmup() {
  if (typeof fetch !== 'function') return
  try {
    fetch(buildUrl('/health/'), { method: 'GET', cache: 'no-store' }).catch(() => {})
  } catch {
    /* 预热失败无所谓，正式请求会给出提示 */
  }
}

/** GET 快捷方式，params 里空值会被自动丢掉 */
export const get = (path, params, options = {}) => request(path, { ...options, method: 'GET', params })

/** POST 快捷方式，body 自动 JSON 序列化 */
export const post = (path, body, options = {}) => request(path, { ...options, method: 'POST', body })
