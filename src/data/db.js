import { reactive, watch } from 'vue'

/**
 * 演示版数据层：全部在浏览器里跑，用 localStorage 持久化。
 * 接口形状刻意做成「异步 + 返回 { ok, message }」，以后换成 Django/DRF 时，
 * 页面里的调用代码一行都不用改，把函数体换成 axios 请求即可。
 */

const LS_KEY = 'what2eat:v1'

export const SOURCES = [
  { key: 'all', label: '全部', emoji: '🎲' },
  { key: 'canteen', label: '食堂', emoji: '🍚' },
  { key: 'takeout', label: '外卖', emoji: '🛵' },
  { key: 'restaurant', label: '饭店', emoji: '🍽️' },
  { key: 'night', label: '夜市', emoji: '🌙' },
]

const SHOPS = [
  { id: 's1', name: '一食堂·三层小炒', source: 'canteen', location: '东区一食堂 3F', emoji: '🍳' },
  { id: 's2', name: '二食堂·麻辣香锅', source: 'canteen', location: '西区二食堂 2F', emoji: '🌶️' },
  { id: 's3', name: '三食堂·兰州拉面', source: 'canteen', location: '南区三食堂 1F', emoji: '🍜' },
  { id: 's4', name: '西门鸡公煲', source: 'restaurant', location: '西门美食街', emoji: '🍲' },
  { id: 's5', name: '阿铭烤肉饭', source: 'takeout', location: '外卖 · 约 30 分钟', emoji: '🍱' },
  { id: 's6', name: '夜市·烤冷面', source: 'night', location: '北门夜市 18:00-23:00', emoji: '🌙' },
]

const DISHES = [
  { id: 'd1', shopId: 's1', name: '鱼香肉丝盖饭', price: 12, category: '盖饭', emoji: '🍛', desc: '微辣，下饭神器', likes: 36, favorites: 12 },
  { id: 'd2', shopId: 's1', name: '番茄炒蛋盖饭', price: 10, category: '盖饭', emoji: '🍅', desc: '酸甜口，永远不会错', likes: 28, favorites: 9 },
  { id: 'd3', shopId: 's1', name: '糖醋里脊', price: 16, category: '热菜', emoji: '🍖', desc: '外酥里嫩，配米饭', likes: 41, favorites: 15 },
  { id: 'd4', shopId: 's2', name: '麻辣香锅（微辣）', price: 18, category: '香锅', emoji: '🌶️', desc: '自选配菜，一碗抵三菜', likes: 52, favorites: 21 },
  { id: 'd5', shopId: 's2', name: '冒菜', price: 15, category: '冒菜', emoji: '🥘', desc: '一个人的火锅', likes: 33, favorites: 10 },
  { id: 'd6', shopId: 's3', name: '牛肉拉面', price: 13, category: '面食', emoji: '🍜', desc: '一清二白三红四绿', likes: 47, favorites: 14 },
  { id: 'd7', shopId: 's3', name: '干拌面', price: 11, category: '面食', emoji: '🍝', desc: '加个蛋更香', likes: 22, favorites: 6 },
  { id: 'd8', shopId: 's4', name: '鸡公煲（小份）', price: 38, category: '火锅', emoji: '🍲', desc: '两人份，越煮越入味', likes: 29, favorites: 17 },
  { id: 'd9', shopId: 's4', name: '干锅花菜', price: 22, category: '热菜', emoji: '🥦', desc: '配米饭一流', likes: 18, favorites: 5 },
  { id: 'd10', shopId: 's5', name: '烤肉饭 + 温泉蛋', price: 19, category: '快餐', emoji: '🍱', desc: '招牌，酱汁给得足', likes: 63, favorites: 25 },
  { id: 'd11', shopId: 's5', name: '照烧鸡腿饭', price: 18, category: '快餐', emoji: '🍗', desc: '甜口，适合不想吃辣', likes: 44, favorites: 13 },
  { id: 'd12', shopId: 's5', name: '咖喱牛肉饭', price: 22, category: '快餐', emoji: '🍛', desc: '微辣，咖喱浓', likes: 31, favorites: 8 },
  { id: 'd13', shopId: 's6', name: '烤冷面（加蛋加肠）', price: 9, category: '小吃', emoji: '🥟', desc: '夜市顶流，排队 5 分钟', likes: 58, favorites: 19 },
  { id: 'd14', shopId: 's6', name: '铁板鱿鱼', price: 15, category: '小吃', emoji: '🦑', desc: '现烤，加辣更香', likes: 26, favorites: 7 },
  { id: 'd15', shopId: 's6', name: '炸串拼盘', price: 12, category: '小吃', emoji: '🍢', desc: '十串任选', likes: 34, favorites: 11 },
  { id: 'd16', shopId: 's1', name: '手工水饺（12 只）', price: 14, category: '面食', emoji: '🥟', desc: '白菜猪肉，现包', likes: 25, favorites: 6 },
]

const shopById = (id) => SHOPS.find((s) => s.id === id)
const dishById = (id) => DISHES.find((d) => d.id === id)

/** 菜品 + 所属档口 + 来源，页面直接用这个视图对象 */
function dishView(dish) {
  const shop = shopById(dish.shopId)
  return { ...dish, shop, source: shop?.source || 'canteen', sourceLabel: SOURCES.find((s) => s.key === shop?.source)?.label || '食堂' }
}

export const allDishViews = () => DISHES.map(dishView)

// ---------------------------------------------------------------------------
// 本地状态
// ---------------------------------------------------------------------------

const USER_KEY = 'guest' // 演示用，真实项目里换成登录用户的 id

function emptyState() {
  return {
    user: { verified: false, studentId: '', name: '', college: '' },
    likes: {},
    favorites: {},
    heat: {},
    eaten: [],
    checkins: [],
    votes: [],
  }
}

export const state = reactive(emptyState())

try {
  const saved = JSON.parse(localStorage.getItem(LS_KEY) || 'null')
  if (saved && typeof saved === 'object') {
    Object.assign(state, saved)
    state.user = { ...emptyState().user, ...(saved.user || {}) }
    state.likes ||= {}
    state.favorites ||= {}
    state.heat ||= {}
    state.eaten ||= []
    state.checkins ||= []
    state.votes ||= []
  }
} catch {
  /* 存储损坏就当第一次打开 */
}

watch(
  state,
  () => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(state))
    } catch {
      /* 图片太大超出配额时忽略，不影响使用 */
    }
  },
  { deep: true },
)

const heatDelta = (id) => (state.heat[id]?.likes || 0) + (state.heat[id]?.favorites || 0)

/** 热度 = 原始点赞收藏 + 本次会话的增量，用于加权随机和人气榜 */
export const heatOf = (dish) => (dish.likes || 0) + (dish.favorites || 0) + heatDelta(dish.id)

// ---------------------------------------------------------------------------
// 随机推荐：加权抽样 + 避开最近吃过的
// ---------------------------------------------------------------------------

export function pickRandom(source = 'all') {
  const pool = allDishViews().filter((d) => source === 'all' || d.source === source)
  if (!pool.length) return null

  const recent = new Set(state.eaten.slice(0, 4).map((e) => e.dishId))
  let candidates = pool.filter((d) => !recent.has(d.id))
  if (!candidates.length) candidates = pool // 全都吃过了就别去重了

  // 权重 = 基础权重 1 + 热度 * 0.06，热度越高越容易被抽中，但冷门菜仍有翻盘机会
  const weights = candidates.map((d) => 1 + heatOf(d) * 0.06)
  const total = weights.reduce((a, b) => a + b, 0)

  let r = Math.random() * total
  for (let i = 0; i < candidates.length; i++) {
    r -= weights[i]
    if (r <= 0) return candidates[i]
  }
  return candidates[candidates.length - 1]
}


// ---------------------------------------------------------------------------
// 点赞 / 收藏
// ---------------------------------------------------------------------------

export function isLiked(id) {
  return !!state.likes[id]
}
export function isFaved(id) {
  return !!state.favorites[id]
}

export function toggleLike(id) {
  const on = !state.likes[id]
  const h = state.heat[id] || (state.heat[id] = { likes: 0, favorites: 0 })
  if (on) {
    state.likes[id] = true
    h.likes += 1
  } else {
    delete state.likes[id]
    h.likes -= 1
  }
  return on
}

export function toggleFavorite(id) {
  const on = !state.favorites[id]
  const h = state.heat[id] || (state.heat[id] = { likes: 0, favorites: 0 })
  if (on) {
    state.favorites[id] = true
    h.favorites += 1
  } else {
    delete state.favorites[id]
    h.favorites -= 1
  }
  return on
}

export function favoriteDishes() {
  return Object.keys(state.favorites)
    .map((id) => dishById(id))
    .filter(Boolean)
    .map(dishView)
}

// ---------------------------------------------------------------------------
// 身份验证：学号 + 姓名 + 学院 三重比对（对应文档 3.5）
// ---------------------------------------------------------------------------

const ROSTER = [
  { studentId: '20230001', name: '张同学', college: '计算机学院' },
  { studentId: '20230002', name: '李同学', college: '外国语学院' },
  { studentId: '20230003', name: '王同学', college: '机械工程学院' },
]

export const DEMO_STUDENT = ROSTER[0]

export function verifyStudent({ studentId, name, college }) {
  const sid = (studentId || '').trim()
  const nm = (name || '').trim()
  const cl = (college || '').trim()

  if (!sid || !nm || !cl) return { ok: false, message: '学号、姓名、学院都要填' }

  // 唯一性：一个学号只能绑一个账号（演示环境只有一个本地账号，仅做提示）
  const hit = ROSTER.find((r) => r.studentId === sid && r.name === nm && r.college === cl)
  if (!hit) return { ok: false, message: '学号、姓名与学院不匹配，未通过核验' }

  state.user = { verified: true, studentId: hit.studentId, name: hit.name, college: hit.college }
  return { ok: true, message: `核验通过，欢迎 ${hit.name}` }
}

// ---------------------------------------------------------------------------
// 备餐打卡
// ---------------------------------------------------------------------------

export function addCheckin({ content, image, dishName, visibility }) {
  if (!state.user.verified) return { ok: false, message: '发布前请先完成学号核验', code: 'UNVERIFIED' }
  if (!content || !content.trim()) return { ok: false, message: '写点什么吧' }

  state.checkins.unshift({
    id: `c${Date.now()}${Math.floor(Math.random() * 1000)}`,
    who: state.user.name || '同学',
    studentId: state.user.studentId,
    content: content.trim(),
    image: image || '',
    dishName: dishName || '',
    visibility: visibility === 'private' ? 'private' : 'public',
    at: Date.now(),
  })
  return { ok: true, message: '打卡成功' }
}

// ---------------------------------------------------------------------------
// 吃不吃投票
// ---------------------------------------------------------------------------

/** 半数以上同意才算「去吃」：同意票 ≥ floor(目标人数 / 2) + 1 */
export const votesNeeded = (targetCount) => Math.floor(Number(targetCount) / 2) + 1

function settle(vote) {
  const need = votesNeeded(vote.targetCount)
  if (vote.agree >= need) vote.status = 'passed'
  else if (vote.disagree >= need) vote.status = 'rejected'
}

export function createVote({ title, target, targetCount }) {
  if (!state.user.verified) return { ok: false, message: '发起投票前请先完成学号核验', code: 'UNVERIFIED' }
  if (!title || !title.trim()) return { ok: false, message: '给投票起个标题' }
  const count = Math.max(2, Math.min(99, Number(targetCount) || 6))
  const vote = {
    id: `v${Date.now()}`,
    title: title.trim(),
    target: (target || '').trim(),
    targetCount: count,
    agree: 0,
    disagree: 0,
    voters: {},
    status: 'ongoing',
    createdAt: Date.now(),
    deadline: Date.now() + 12 * 3600 * 1000,
  }
  state.votes.unshift(vote)
  return { ok: true, vote }
}

export function castVote(voteId, option, voterId) {
  const vote = state.votes.find((v) => v.id === voteId)
  if (!vote) return { ok: false, message: '投票不存在' }
  if (vote.status !== 'ongoing') return { ok: false, message: '这个投票已经结束了' }
  if (Date.now() > vote.deadline) {
    vote.status = 'expired'
    return { ok: false, message: '投票已截止' }
  }

  const uid = voterId || (state.user.verified ? state.user.studentId : USER_KEY)
  if (vote.voters[uid]) return { ok: false, message: '每人只能投一票' }

  vote.voters[uid] = option
  if (option === 'agree') vote.agree += 1
  else vote.disagree += 1

  settle(vote)
  return { ok: true }
}

/** 演示辅助：模拟其他同学投票，否则一个人点不出「过半」的效果 */
export function simulateVotes(voteId, count = 1) {
  const options = ['agree', 'agree', 'agree', 'disagree']
  let done = 0
  for (let i = 0; i < count; i++) {
    const uid = `sim-${Math.random().toString(36).slice(2, 8)}`
    const res = castVote(voteId, options[Math.floor(Math.random() * options.length)], uid)
    if (res.ok) done += 1
  }
  return done
}

export const voteStatusText = (vote) =>
  ({ ongoing: '进行中', passed: '通过 · 去吃', rejected: '未通过 · 算了', expired: '已截止' })[vote.status] || '进行中'

// ---------------------------------------------------------------------------
// 时间格式化
// ---------------------------------------------------------------------------

export function fmtTime(ts) {
  const diff = Date.now() - ts
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 3600 * 1000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400 * 1000) return `${Math.floor(diff / 3600000)} 小时前`
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
