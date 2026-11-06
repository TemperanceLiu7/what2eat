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

export async function addCheckin({ content, image, dishName } = {}) {
  return db.addCheckin({ content, image, dishName })
}

export async function createVote({ title, target, targetCount } = {}) {
  return db.createVote({ title, target, targetCount })
}

export async function castVote(voteId, option) {
  return db.castVote(voteId, option)
}
