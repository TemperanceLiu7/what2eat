import * as db from '@/data/db'
import { setToken } from './client'

/**
 * mock 适配器：数据仍然是 db.js 里那套 localStorage 演示数据，只是全部改成
 * 异步返回，让页面提前按「接口调用」的方式写。默认开启，只有显式写
 * VITE_USE_MOCK=false 才会走真实 HTTP，所以线上站点不受影响。
 *
 * 说明：db.js 里没有 login / register（演示版没有账号体系），这里按契约补了
 * 一个最小的本地实现，接口开发期间也能把登录跑通。
 */

/** mock 环境下没有后端，演示账号就是 db.js 里的那个学号 */
const DEMO_PASSWORD = '123456'

/** 造一个只在本地有效的假 token，方便页面走鉴权分支 */
const fakeToken = () => `mock.${Date.now().toString(36)}`

// ---------------------------------------------------------------------------
// 核验 / 登录
// ---------------------------------------------------------------------------

export async function verifyStudent({ studentId, name, college } = {}) {
  const res = db.verifyStudent({ studentId, name, college })
  // db 核验通过会直接写 state.user，这里把用户带回去，形状和真接口对齐
  return res.ok ? { ...res, user: { ...db.state.user } } : res
}

export async function login({ username, password } = {}) {
  const user = (username || '').trim()
  if (!user || !password) return { ok: false, message: '请输入账号和密码', code: 'INVALID_DATA' }

  if (user !== db.DEMO_STUDENT.studentId || password !== DEMO_PASSWORD) {
    return { ok: false, message: `账号或密码不对（演示账号 ${db.DEMO_STUDENT.studentId} / ${DEMO_PASSWORD}）`, code: 'INVALID_DATA' }
  }

  // 登录成功顺手完成核验，否则接着发打卡 / 投票会卡在 UNVERIFIED
  db.verifyStudent(db.DEMO_STUDENT)
  const token = fakeToken()
  setToken(token)
  return { ok: true, message: `登录成功，欢迎 ${db.DEMO_STUDENT.name}`, token, user: { ...db.state.user } }
}

export async function register({ username, password, name, studentId, college } = {}) {
  const user = (username || '').trim()
  if (!user || !password) return { ok: false, message: '账号和密码都要填', code: 'INVALID_DATA' }
  if (String(password).length < 6) return { ok: false, message: '密码至少 6 位', code: 'INVALID_DATA' }

  // mock 不落库，注册完直接给登录态；学号唯一性这些校验留给真后端
  const token = fakeToken()
  setToken(token)
  return {
    ok: true,
    message: '注册成功（mock）',
    token,
    user: {
      username: user,
      name: (name || '').trim() || user,
      studentId: (studentId || '').trim(),
      college: (college || '').trim(),
      verified: false,
    },
  }
}

// ---------------------------------------------------------------------------
// 随机推荐 / 点赞 / 收藏
// ---------------------------------------------------------------------------

export async function pickRandom(source = 'all') {
  return db.pickRandom(source)
}

export async function toggleLike(targetType, targetId) {
  // 兼容两种写法：新契约 toggleLike('dish', 'd1')，旧页面 toggleLike('d1')
  const id = targetId === undefined ? targetType : targetId
  return db.toggleLike(id)
}

export async function toggleFavorite(targetType, targetId) {
  const id = targetId === undefined ? targetType : targetId
  return db.toggleFavorite(id)
}

export async function favoriteDishes() {
  return db.favoriteDishes()
}

// ---------------------------------------------------------------------------
// 打卡 / 投票
// ---------------------------------------------------------------------------

export async function addCheckin({ content, image, dishName, visibility } = {}) {
  return db.addCheckin({ content, image, dishName, visibility })
}

export async function createVote({ title, target, targetCount } = {}) {
  return db.createVote({ title, target, targetCount })
}

export async function castVote(voteId, option) {
  return db.castVote(voteId, option)
}

/** 申请复审：按同一套规则在本地复制一个新投票，目标人数放大 1.5 倍 */
export async function requestReview(voteId) {
  const vote = db.state.votes.find((v) => v.id === voteId)
  if (!vote) return { ok: false, message: '投票不存在', code: 'NOT_FOUND' }
  if (vote.reviewOf) return { ok: false, message: '复审投票不能再申请复审', code: 'INVALID_DATA' }
  if (vote.status === 'ongoing') {
    return { ok: false, message: '投票还在进行中，等出结果后再申请复审', code: 'INVALID_DATA' }
  }
  if (db.state.votes.some((v) => v.reviewOf === voteId)) {
    return { ok: false, message: '这个投票已经复审过了', code: 'INVALID_DATA' }
  }

  const expanded = Math.min(99, vote.targetCount + Math.max(2, Math.floor(vote.targetCount / 2)))
  const review = {
    id: `v${Date.now()}`,
    title: `复审：${vote.title}`.slice(0, 100),
    target: vote.target || '',
    targetCount: expanded,
    agree: 0,
    disagree: 0,
    voters: {},
    status: 'ongoing',
    createdAt: Date.now(),
    deadline: Date.now() + 12 * 3600 * 1000,
    reviewOf: voteId,
  }
  db.state.votes.unshift(review)
  return {
    ok: true,
    message: `已发起复审，参与人数扩大到 ${expanded} 人`,
    vote: review,
    targetCount: expanded,
  }
}

// ---------------------------------------------------------------------------
// 列表 / 其他（真接口模式下有对应实现，mock 直接读本地 state）
// ---------------------------------------------------------------------------

export async function listCheckins(scope) {
  const all = [...db.state.checkins]
  if (scope === 'mine') return all
  // 演示数据没有 visibility 字段，全当公开
  return all.filter((c) => (c.visibility || 'public') === 'public')
}

/** mock 没有视觉模型：直接告诉前端「没开」，页面会降级成手动选菜 */
export async function recognizeImage() {
  return { dishes: [], note: '演示模式没有接识别服务，手动选一下就好', ready: false }
}

/** 演示版的偏好画像：从本地打卡里数出来 */
export async function loadPreferences() {
  const items = db.state.checkins || []
  const names = {}
  const cats = {}
  for (const c of items) {
    const name = c.dishName || c.content?.slice(0, 8) || ''
    if (name) names[name] = (names[name] || 0) + 1
  }
  const weekAgo = Date.now() - 7 * 24 * 3600 * 1000
  return {
    totalCheckins: items.length,
    last7Days: items.filter((c) => c.at >= weekAgo).length,
    privateCount: items.filter((c) => c.visibility === 'private').length,
    topDishes: Object.entries(names)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({ name, count })),
    topCategories: [],
    topSources: [],
  }
}

export async function listVotes() {
  return [...db.state.votes]
}

export async function simulateVotes(voteId, count = 2) {
  const n = db.simulateVotes(voteId, count)
  return { ok: true, message: n ? `模拟 ${n} 位同学投了票` : '这个投票已经结束', count: n }
}

export async function logout() {
  setToken('')
  // mock 没有账号体系，退出就把本地核验状态清掉
  db.state.user = { verified: false, studentId: '', name: '', college: '' }
  return { ok: true, message: '已退出登录' }
}

/** 演示版的举报：只记在内存里，够把交互跑通 */
const mockReports = []

export async function report({ reportedId, targetType, targetId, reason } = {}) {
  if (!reason || !String(reason).trim()) {
    return { ok: false, message: '请填写举报原因', code: 'INVALID_DATA' }
  }
  const dup = mockReports.find(
    (r) => r.reportedId === reportedId && r.targetType === targetType && r.targetId === targetId,
  )
  if (dup) return { ok: false, message: '你已经举报过这条内容，正在处理中', code: 'INVALID_DATA' }

  mockReports.push({ reportedId, targetType, targetId, reason })
  return { ok: true, message: '举报已提交（演示模式，不会真的处罚）', reportCount: mockReports.length }
}
