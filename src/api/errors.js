/**
 * 错误码 → 中文提示。
 * 后端业务码（UNVERIFIED / BANNED ...）放在 ApiError.code 里；
 * 网络层的问题（超时、断网、401/403/500）由 client.js 兜底成同名 code，
 * 所以页面里只要一句 `messageOf(err)` 就能拿到能给人看的文案。
 */

export const ERROR_MESSAGES = {
  // ---- 后端业务码，和另一位同学约定好的那批 ----
  UNVERIFIED: '请先完成学号核验',
  BANNED: '该账号已被封禁，无法操作',
  ALREADY_VOTED: '你已经投过票了，每人只能投一次',
  VOTE_CLOSED: '投票已结束，不能再投',
  INVALID_DATA: '提交的数据不合法，请检查后重试',

  // ---- 传输层 / 鉴权兜底 ----
  TIMEOUT: '服务响应超时，可能正在冷启动，请再试一次',
  NETWORK: '连不上服务器，请检查网络后重试',
  UNAUTHORIZED: '登录状态已失效，请重新登录',
  FORBIDDEN: '没有权限执行这个操作',
  NOT_FOUND: '请求的内容不存在',
  TOO_MANY_REQUESTS: '操作太频繁，歇一会儿再试',
  SERVER_ERROR: '服务器开小差了，请稍后再试',
  BAD_RESPONSE: '服务器返回了异常内容，请稍后再试',
  UNKNOWN: '操作失败，请稍后再试',
}

/** HTTP 状态码 → 默认提示（后端没给 message 时兜底） */
const STATUS_MESSAGES = {
  400: '请求参数有误',
  401: '登录状态已失效，请重新登录',
  403: '没有权限执行这个操作',
  404: '请求的内容不存在',
  429: '操作太频繁，歇一会儿再试',
  500: '服务器开小差了，请稍后再试',
  502: '服务器开小差了，请稍后再试',
  503: '服务暂时不可用，请稍后再试',
}

/** HTTP 状态码 → 业务码，方便统一按 code 处理 */
const STATUS_CODES = {
  400: 'INVALID_DATA',
  401: 'UNAUTHORIZED',
  403: 'FORBIDDEN',
  404: 'NOT_FOUND',
  429: 'TOO_MANY_REQUESTS',
  500: 'SERVER_ERROR',
  502: 'SERVER_ERROR',
  503: 'SERVER_ERROR',
}

/** 后端没返回 code 时，按状态码猜一个 */
export function codeOfStatus(status) {
  if (STATUS_CODES[status]) return STATUS_CODES[status]
  if (status >= 500) return 'SERVER_ERROR'
  return 'UNKNOWN'
}

/**
 * 把任意错误翻译成中文提示。
 * 顺序：已经是中文的 message（后端给的更具体，优先）→ 业务码 → HTTP 状态码 → 通用兜底。
 * @param {unknown} err ApiError / Error / 错误码字符串
 * @returns {string}
 */
export function messageOf(err) {
  if (!err) return ERROR_MESSAGES.UNKNOWN
  if (typeof err === 'string') return ERROR_MESSAGES[err] || err

  // 后端在 message 里给了中文就看它的，别用「登录状态已失效」盖掉「账号或密码错误」
  const raw = typeof err.message === 'string' ? err.message : ''
  if (/[\u4e00-\u9fa5]/.test(raw)) return raw

  // UNKNOWN 不算有效业务码，跳过它，好让下面的状态码有机会生效
  if (err.code && err.code !== 'UNKNOWN' && ERROR_MESSAGES[err.code]) return ERROR_MESSAGES[err.code]
  if (err.status && STATUS_MESSAGES[err.status]) return STATUS_MESSAGES[err.status]

  return ERROR_MESSAGES.UNKNOWN
}
