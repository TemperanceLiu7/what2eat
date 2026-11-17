<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { SOURCES, allDishViews, heatOf, isLiked, isFaved } from '@/data/db'
import { pickRandom, toggleFavorite, toggleLike } from '@/api'
import { pushEaten, ui } from '@/stores/app'
import { toast } from '@/composables/useToast'
import { useIsMobile } from '@/composables/useIsMobile'

const router = useRouter()
const isMobile = useIsMobile()

const source = ref('all')
const dish = ref(null)
const rolling = ref(false)
// 抽签序号：让「同一道菜再次中签」也能重播入场动画（key 里带上它）
const drawSeq = ref(0)

// 各主题横幅贴纸（右上角 / 左下角）与抽签彩带配色
const STICKERS = {
  latte: { top: '☕', bottom: '🍰' },
  lemon: { top: '🍋', bottom: '🥤' },
  peach: { top: '🍑', bottom: '🍨' },
}
const CONFETTI_COLORS = {
  latte: ['#b5673f', '#e9b44c', '#f4edd9', '#8a5a44', '#7d9168', '#e8913f'],
  lemon: ['#6faecf', '#efc65e', '#fdfaf0', '#5796b6', '#7fb8d6', '#a6d0e6'],
  peach: ['#e08280', '#fbdca5', '#fff3f3', '#c96664', '#f69e9d', '#f8c3cb'],
}
const stickerTop = computed(() => STICKERS[ui.theme]?.top || STICKERS.latte.top)
const stickerBottom = computed(() => STICKERS[ui.theme]?.bottom || STICKERS.latte.bottom)

const confetti = ref([])
let confettiSeq = 0
function burstConfetti() {
  const colors = CONFETTI_COLORS[ui.theme] || CONFETTI_COLORS.latte
  confetti.value = Array.from({ length: 24 }, (_, i) => ({
    id: ++confettiSeq,
    left: 6 + Math.random() * 88,
    delay: Math.random() * 0.16,
    duration: 1.4 + Math.random() * 1.1,
    color: colors[i % colors.length],
    rotate: Math.random() * 720 - 360,
    drift: Math.random() * 140 - 70,
    round: i % 3 === 0,
    size: 6 + Math.random() * 6,
  }))
  window.setTimeout(() => {
    confetti.value = []
  }, 2800)
}

const liked = ref(false)
const faved = ref(false)

const heat = computed(() => (dish.value ? heatOf(dish.value) : 0))

const hot = computed(() =>
  allDishViews()
    .map((d) => ({ ...d, heat: heatOf(d) }))
    .sort((a, b) => b.heat - a.heat)
    .slice(0, 5),
)

const recent = computed(() => ui.eaten.slice(0, 3))

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function syncFlags(d) {
  if (!d) {
    liked.value = false
    faved.value = false
    return
  }
  liked.value = d.liked ?? isLiked(d.id)
  faved.value = d.favorited ?? isFaved(d.id)
}

async function roll() {
  if (rolling.value) return
  enableShake()
  if (navigator.vibrate) navigator.vibrate(15)

  rolling.value = true
  await sleep(520)
  try {
    const picked = await pickRandom(source.value)
    dish.value = picked
    drawSeq.value += 1
    syncFlags(picked)
    if (picked) {
      pushEaten(picked)
      burstConfetti()
    }
  } catch (err) {
    toast(err?.message || '抽签失败，稍后再试')
  } finally {
    rolling.value = false
  }
  if (navigator.vibrate) navigator.vibrate(8)
}

function needLogin(err) {
  if (err?.status === 401) {
    toast('请先登录')
    router.push({ path: '/login', query: { redirect: '/' } })
    return true
  }
  return false
}

async function like() {
  if (!dish.value) return
  try {
    liked.value = await toggleLike('dish', dish.value.id)
    toast(liked.value ? '已点赞，会略微提高它的中签率' : '已取消点赞')
  } catch (err) {
    if (!needLogin(err)) toast(err?.message || '操作失败')
  }
}

async function fav() {
  if (!dish.value) return
  try {
    faved.value = await toggleFavorite('dish', dish.value.id)
    toast(faved.value ? '已收藏，去「我的」查看' : '已取消收藏')
  } catch (err) {
    if (!needLogin(err)) toast(err?.message || '操作失败')
  }
}

// 由菜品热度派生「月售」，给商品卡一个真实的商业信息维度（纯展示，不改数据层）
function monthlySales(d) {
  return Math.max(28, Math.round((d.likes || 0) * 2.4 + (d.favorites || 0) * 3.1))
}

// 手机甩动抽签
let motionBound = false
async function enableShake() {
  if (motionBound) return
  if (typeof DeviceMotionEvent === 'undefined') return
  if (typeof DeviceMotionEvent.requestPermission === 'function') {
    try {
      const res = await DeviceMotionEvent.requestPermission()
      if (res !== 'granted') return
    } catch {
      return
    }
  }
  motionBound = true
  let last = 0
  window.addEventListener('devicemotion', (e) => {
    const a = e.accelerationIncludingGravity
    if (!a) return
    const mag = Math.abs(a.x || 0) + Math.abs(a.y || 0) + Math.abs(a.z || 0)
    const now = Date.now()
    if (mag > 30 && now - last > 900) {
      last = now
      roll()
    }
  })
}
</script>

<template>
  <div class="page home">
    <!-- 手帐主卡：米白波点纸框 + 棕纸内页 + 胶带枝叶 + 贴纸 -->
    <section class="promo-banner">
      <div class="dotted-frame">
        <div class="frame-body">
          <span class="tape-sprig tape-top" aria-hidden="true"></span>
          <span class="tape-sprig tape-bottom" aria-hidden="true"></span>
          <span class="sticker sticker-cup" aria-hidden="true">{{ stickerTop }}</span>
          <span class="sticker sticker-cake" aria-hidden="true">{{ stickerBottom }}</span>
          <div class="banner-copy">
            <div class="banner-tag"><span class="tag-flash">⚡</span> 校园专属 · 每日精选</div>
            <h1>今天吃<span>什么</span>？</h1>
            <p>选择困难？一键随机，摇到就吃</p>
            <div class="banner-points">
              <span><i>✓</i> 全网比价</span>
              <span><i>✓</i> 人气加权</span>
              <span><i>✓</i> 学生认证</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 金刚区：来源分类图标导航 -->
    <nav class="category-nav card" aria-label="推荐范围">
      <button
        v-for="s in SOURCES"
        :key="s.key"
        class="category"
        :class="{ active: source === s.key }"
        @click="source = s.key"
      >
        <span class="category-icon">{{ s.emoji }}</span>
        <span class="category-label">{{ s.label }}</span>
      </button>
    </nav>

    <div class="home-grid">
      <section class="draw">
        <!-- 主抽签卡：商品卡质感 -->
        <div class="draw-card card">
          <div class="card-headline">
            <div>
              <h2>今日随机推荐</h2>
              <p>摇一摇，把选择交给运气</p>
            </div>
            <span class="live-badge"><i></i> 实时更新</span>
          </div>

          <div class="slot" :class="{ rolling }" :aria-busy="rolling" aria-live="polite">
            <div class="confetti-layer" aria-hidden="true">
              <i
                v-for="b in confetti"
                :key="b.id"
                class="confetti"
                :class="{ round: b.round }"
                :style="{
                  left: b.left + '%',
                  background: b.color,
                  width: b.size + 'px',
                  height: (b.round ? b.size : b.size * 1.7) + 'px',
                  '--delay': b.delay + 's',
                  '--dur': b.duration + 's',
                  '--rot': b.rotate + 'deg',
                  '--drift': b.drift + 'px',
                }"
              />
            </div>

            <Transition name="reveal" mode="out-in">
              <div v-if="dish" :key="`${dish.id}-${drawSeq}`" class="result">
                <div class="result-pic rise" style="--d: 0ms">
                  <span class="result-emoji">{{ dish.emoji }}</span>
                  <span class="pic-badge">今日推荐</span>
                </div>
                <div class="result-info">
                  <h3 class="result-name rise" style="--d: 60ms">{{ dish.name }}</h3>
                  <div class="result-stats rise" style="--d: 100ms">
                    <span class="score"><b>4.8</b> 分</span>
                    <span class="sales">月售 {{ monthlySales(dish) }}</span>
                    <span class="eta">≈ 15 分钟</span>
                  </div>
                  <div class="result-tags rise" style="--d: 140ms">
                    <span class="rtag red">满20减5</span>
                    <span class="rtag orange">{{ dish.category }}</span>
                    <span class="rtag">{{ dish.sourceLabel }}</span>
                  </div>
                  <div class="result-bottom rise" style="--d: 190ms">
                    <div class="price-wrap">
                      <span class="currency">¥</span><span class="price">{{ dish.price }}</span>
                      <span class="price-origin">¥{{ dish.price + 6 }}</span>
                    </div>
                    <div class="result-actions">
                      <button class="icon-btn" :class="{ on: faved }" @click="fav" :aria-label="faved ? '取消收藏' : '收藏'">
                        <span>{{ faved ? '★' : '☆' }}</span>
                      </button>
                      <button class="icon-btn" :class="{ on: liked }" @click="like" :aria-label="liked ? '取消点赞' : '点赞'">
                        <span>{{ liked ? '♥' : '♡' }}</span>
                      </button>
                      <button class="go-btn" @click="router.push('/checkin')">去打卡 →</button>
                    </div>
                  </div>
                  <p class="result-shop rise" style="--d: 230ms">{{ dish.shop.emoji }} {{ dish.shop.name }} · {{ dish.shop.location }} · 🔥 {{ heat }}</p>
                </div>
              </div>

              <div v-else key="empty" class="result-empty">
                <div class="empty-plate">🍽️</div>
                <p class="empty-title">万事俱备，等你开摇</p>
                <p class="empty-sub">点击下方按钮，抽取今天的专属美味</p>
              </div>
            </Transition>
          </div>

          <button class="roll-btn" :class="{ 'is-rolling': rolling }" @click="roll">
            <span class="roll-icon" aria-hidden="true">🎲</span>
            <span>{{ rolling ? '正在为你抽取…' : dish ? '再摇一次' : '摇一摇，帮我决定' }}</span>
            <span class="roll-arrow" aria-hidden="true">→</span>
          </button>
          <p class="hint">
            <template v-if="isMobile">也可以直接甩动手机抽签</template>
            <template v-else>热度高的菜会被加权抽中</template>
            · 当前范围 <b>{{ SOURCES.find((s) => s.key === source).label }}</b>
          </p>
        </div>

        <!-- 移动端：最近抽到 -->
        <section v-if="recent.length" class="recent-rail">
          <div class="rail-head"><h2>最近摇到</h2><span>自动避开，不重样</span></div>
          <ul class="rail">
            <li v-for="(d, i) in recent" :key="d.id" class="rail-item" :style="{ '--i': i }">
              <span class="rail-emoji">{{ d.emoji }}</span>
              <span class="rail-name">{{ d.name }}</span>
              <span class="rail-price">¥{{ d.price }}</span>
            </li>
          </ul>
        </section>
      </section>

      <aside class="side">
        <section class="side-card card">
          <div class="side-head">
            <h2>🔥 本周热销榜</h2>
            <span>按点赞收藏</span>
          </div>
          <ol class="rank">
            <li v-for="(d, i) in hot" :key="d.id">
              <span class="rank-no" :class="`rank-no-${i + 1}`">{{ i + 1 }}</span>
              <span class="rank-thumb">{{ d.emoji }}</span>
              <span class="rank-mid">
                <span class="rank-name">{{ d.name }}</span>
                <span class="rank-sub">月售 {{ monthlySales(d) }} · ⭐ 4.8</span>
              </span>
              <span class="rank-price">¥{{ d.price }}</span>
            </li>
          </ol>
        </section>

        <section v-if="recent.length" class="side-card card side-recent">
          <div class="side-head"><h2>🕒 最近摇到</h2><span>已自动避开</span></div>
          <ul class="recent">
            <li v-for="d in recent" :key="d.id">
              <span class="rank-thumb">{{ d.emoji }}</span>
              <span class="rank-name">{{ d.name }}</span>
              <span class="rank-price">¥{{ d.price }}</span>
            </li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.home {
  --draw-dur: 0.52s;
  --rise-dur: 0.38s;
  --hot: var(--brand-strong);
  --hot-deep: var(--kraft-deep);
  --gold: var(--brand-2);
}

/* ---------- 手帐主卡（波点纸框 + 棕纸内页） ---------- */
.promo-banner {
  margin-bottom: 18px;
}

.frame-body {
  position: relative;
  min-height: 208px;
  padding: 36px 36px;
  color: var(--cream);
}

.tape-top {
  position: absolute;
  top: 5px;
  left: 26px;
  right: 26px;
}

.tape-bottom {
  position: absolute;
  bottom: 5px;
  left: 26px;
  right: 26px;
}

.sticker-cup {
  position: absolute;
  top: 18px;
  right: 28px;
  font-size: 34px;
  transform: rotate(8deg);
}

.sticker-cake {
  position: absolute;
  bottom: 20px;
  left: 24px;
  font-size: 30px;
  transform: rotate(-7deg);
}

.banner-copy {
  position: relative;
  z-index: 1;
  max-width: 66%;
}

.banner-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(244, 237, 217, 0.16);
  border: 1px solid rgba(244, 237, 217, 0.3);
  margin-bottom: 14px;
}

.tag-flash { font-size: 13px; }

.banner-copy h1 {
  font-family: var(--font-hand);
  font-size: 42px;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: 0.01em;
  color: var(--cream);
  text-shadow: 0 2px 8px rgba(60, 30, 18, 0.25);
}
.banner-copy h1 span { color: var(--brand-2); }

.banner-copy > p {
  margin-top: 8px;
  font-size: 16px;
  font-weight: 500;
  opacity: 0.96;
}

.banner-points {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  margin-top: 20px;
}
.banner-points span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}
.banner-points i {
  font-style: normal;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: var(--cream);
  color: var(--kraft-deep);
  font-size: 11px;
  font-weight: 800;
}

/* ---------- 金刚区 ---------- */
.category-nav {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
  padding: 18px 10px;
  margin-bottom: 18px;
}

.category {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  border: none;
  background: transparent;
  border-radius: 14px;
  transition: transform var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.category:hover { transform: translateY(-3px); background: var(--brand-soft); }
.category.active { background: var(--surface-soft); }

.category-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  font-size: 26px;
  border-radius: 18px;
  background: linear-gradient(145deg, var(--brand-soft), var(--surface-soft));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 4px 10px rgba(138, 90, 68, 0.14);
  transition: all var(--dur-fast) var(--ease-out);
}
.category.active .category-icon {
  background: var(--brand-grad);
  box-shadow: 0 6px 16px var(--brand-glow);
  transform: scale(1.06);
}
.category-label { font-size: 13px; font-weight: 600; color: var(--ink-soft); }
.category.active .category-label { color: var(--hot); font-weight: 700; }

/* ---------- 主栅格 ---------- */
.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.85fr);
  gap: 18px;
  align-items: start;
}
.draw, .recent-rail { min-width: 0; }

.draw-card { padding: 22px; }

.card-headline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.card-headline h2 { font-family: var(--font-hand); font-size: 20px; font-weight: 700; }
.card-headline p { margin-top: 4px; font-size: 12px; color: var(--muted); }

.live-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--hot);
  background: var(--brand-soft);
  border-radius: 999px;
  padding: 6px 10px;
  white-space: nowrap;
}
.live-badge i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--hot);
  animation: live-pulse 1.6s ease-in-out infinite;
}
@keyframes live-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(168, 90, 51, 0.5); }
  50% { box-shadow: 0 0 0 5px rgba(168, 90, 51, 0); }
}

/* ---------- 抽签舞台 / 商品卡 ---------- */
.slot {
  position: relative;
  isolation: isolate;
  border-radius: 16px;
  background: var(--surface-warm);
  border: 1px solid var(--line);
  min-height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  overflow: hidden;
}
.slot::before {
  content: '';
  position: absolute;
  inset: -18%;
  z-index: 0;
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(circle at 50% 46%, var(--brand-glow) 0%, transparent 62%);
}
.slot::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  opacity: 0;
  transform: translateX(-120%);
  background: linear-gradient(105deg, transparent 32%, rgba(255, 255, 255, 0.75) 48%, transparent 64%);
}
.slot.rolling { animation: slot-flow var(--draw-dur) var(--ease-out) both; }
.slot.rolling::before { animation: aura-pulse var(--draw-dur) var(--ease-out) both; }
.slot.rolling::after { animation: sheen-sweep var(--draw-dur) var(--ease-out) both; }

@keyframes slot-flow {
  0% { background-position: 0% 50%; }
  55% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes aura-pulse {
  0% { opacity: 0; transform: scale(0.9); }
  35% { opacity: 0.9; transform: scale(1); }
  70% { opacity: 0.45; transform: scale(1.06); }
  100% { opacity: 0; transform: scale(1.02); }
}
@keyframes sheen-sweep {
  0% { opacity: 0; transform: translateX(-120%); }
  20% { opacity: 1; }
  70% { opacity: 0.9; transform: translateX(120%); }
  100% { opacity: 0; transform: translateX(120%); }
}

.confetti-layer { position: absolute; inset: 0; z-index: 3; pointer-events: none; overflow: hidden; border-radius: inherit; }
.confetti {
  position: absolute; top: -14px; display: block; border-radius: 2px; opacity: 0;
  animation: confetti-fall var(--dur) var(--ease-out) var(--delay) forwards;
}
.confetti.round { border-radius: 50%; }
@keyframes confetti-fall {
  0% { opacity: 0; transform: translate3d(0, -10px, 0) rotate(0); }
  8% { opacity: 1; }
  100% { opacity: 0; transform: translate3d(var(--drift), 320px, 0) rotate(var(--rot)); }
}

.result {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 18px;
  width: 100%;
  padding: 22px;
  animation: card-in var(--draw-dur) var(--ease-out) both;
}
@keyframes card-in {
  0% { opacity: 0; transform: scale(0.94) translateY(12px); filter: blur(6px); }
  100% { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
}

.result-pic {
  position: relative;
  flex: 0 0 132px;
  height: 132px;
  border-radius: 16px;
  background: linear-gradient(145deg, var(--brand-soft), var(--surface-soft));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 8px 18px rgba(138, 90, 68, 0.16);
}
.result-emoji { font-size: 74px; line-height: 1; filter: drop-shadow(0 8px 10px rgba(120, 60, 30, 0.2)); }
.pic-badge {
  position: absolute;
  left: -6px;
  top: 10px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: var(--brand-grad);
  padding: 4px 9px 4px 8px;
  border-radius: 6px 6px 6px 0;
  box-shadow: 0 3px 8px var(--brand-glow);
}

.result-info { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
.result-name { font-family: var(--font-hand); font-size: 24px; font-weight: 700; letter-spacing: 0.01em; line-height: 1.3; }
.result-stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--ink-soft);
}
.result-stats .score { color: var(--gold); font-weight: 700; }
.result-stats .score b { font-size: 15px; }
.result-stats .sales, .result-stats .eta { position: relative; }
.result-stats .sales::after, .result-stats .eta::after {
  content: '';
  position: absolute;
  right: -6px;
  top: 50%;
  width: 1px;
  height: 10px;
  background: var(--line);
  transform: translateY(-50%);
}
.result-stats .eta::after { display: none; }

.result-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.rtag {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 5px;
  color: var(--ink-soft);
  background: var(--surface-soft);
  border: 1px solid transparent;
}
.rtag.red { color: var(--hot); background: var(--brand-soft); border-color: var(--brand-line-soft); }
.rtag.orange { color: var(--brand-2-deep); background: var(--brand-line-soft); border-color: var(--brand-line); }

.result-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-top: auto;
  padding-top: 14px;
}
.price-wrap { display: flex; align-items: baseline; color: var(--hot); }
.price-wrap .currency { font-size: 15px; font-weight: 700; }
.price-wrap .price { font-size: 32px; font-weight: 800; line-height: 1; letter-spacing: -0.02em; }
.price-wrap .price-origin { font-size: 12px; color: var(--muted); text-decoration: line-through; margin-left: 8px; }

.result-actions { display: flex; align-items: center; gap: 8px; }
.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--cream);
  color: var(--muted);
  font-size: 20px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--dur-fast) var(--ease-out);
}
.icon-btn:hover { transform: scale(1.08); border-color: var(--brand-line); color: var(--hot); }
.icon-btn.on { color: var(--hot); border-color: var(--brand-line); background: var(--brand-soft); }
.go-btn {
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: var(--brand-grad);
  box-shadow: 0 5px 12px var(--brand-glow);
  transition: transform var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out);
}
.go-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 18px rgba(168, 90, 51, 0.38); }

.result-shop { margin-top: 12px; font-size: 12px; color: var(--muted); }

.result-empty { position: relative; z-index: 1; text-align: center; padding: 30px 20px; }
.empty-plate { font-size: 68px; line-height: 1; filter: drop-shadow(0 8px 12px rgba(120, 60, 30, 0.15)); }
.empty-title { margin-top: 14px; font-family: var(--font-hand); font-size: 18px; font-weight: 700; color: var(--ink-soft); }
.empty-sub { margin-top: 6px; font-size: 13px; color: var(--muted); }

/* ---------- 主按钮 ---------- */
.roll-btn {
  position: relative;
  width: 100%;
  min-height: 56px;
  border: none;
  border-radius: 14px;
  color: var(--cream);
  font-family: var(--font-hand);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.03em;
  cursor: pointer;
  background: var(--brand-grad);
  background-size: 200% 100%;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 8px 20px var(--brand-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  animation: roll-shine 3.2s var(--ease-out) infinite;
  transition: transform var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out);
}
.roll-btn:hover { transform: translateY(-2px); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 12px 26px rgba(168, 90, 51, 0.42); }
.roll-btn:active { transform: translateY(0) scale(0.99); }
@keyframes roll-shine {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.roll-icon { font-size: 22px; animation: dice-wiggle 2.4s var(--ease-out) infinite; }
.roll-arrow { font-size: 20px; font-weight: 400; opacity: 0.9; }
@keyframes dice-wiggle {
  0%, 100% { transform: rotate(-10deg); }
  50% { transform: rotate(12deg); }
}
.roll-btn.is-rolling { animation: btn-pulse var(--draw-dur) var(--ease-out) both; }
.roll-btn.is-rolling .roll-icon { animation: none; }
@keyframes btn-pulse {
  0% { box-shadow: 0 0 0 0 rgba(168, 90, 51, 0.5), inset 0 1px 0 rgba(255,255,255,.25); transform: scale(1); }
  50% { box-shadow: 0 0 0 10px rgba(168, 90, 51, 0), inset 0 1px 0 rgba(255,255,255,.25); transform: scale(1.015); }
  100% { box-shadow: 0 0 0 0 rgba(168, 90, 51, 0), inset 0 1px 0 rgba(255,255,255,.25); transform: scale(1); }
}

.hint { margin-top: 12px; font-size: 12px; color: var(--muted); text-align: center; line-height: 1.7; }
.hint b { color: var(--hot); }

/* ---------- 入场错峰 ---------- */
.rise { animation: rise var(--rise-dur) var(--ease-back) both; animation-delay: var(--d, 0ms); }
@keyframes rise {
  from { opacity: 0; transform: translateY(10px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.reveal-enter-active { transition: opacity 0.26s var(--ease-out), transform 0.44s var(--ease-back), filter 0.44s var(--ease-out); }
.reveal-leave-active { transition: opacity 0.16s ease, transform 0.2s ease, filter 0.2s ease; }
.reveal-enter-from { opacity: 0; transform: translateY(18px) scale(0.94); filter: blur(7px); }
.reveal-leave-to { opacity: 0; transform: translateY(-8px) scale(0.98); filter: blur(5px); }

/* ---------- 侧栏热销榜 ---------- */
.side { display: flex; flex-direction: column; gap: var(--space-16); }
.side-card { padding: 18px; }
.side-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
.side-head h2 { font-family: var(--font-hand); font-size: 16px; font-weight: 700; }
.side-head span { font-size: 11px; color: var(--muted); }

.rank, .recent { list-style: none; margin: 0; padding: 0; }
.rank li { display: flex; align-items: center; gap: 8px; padding: 10px 0; border-bottom: 1px dashed var(--line); }
.rank li:last-child, .recent li:last-child { border-bottom: none; }
.rank-no {
  flex: 0 0 20px; height: 20px; border-radius: 6px;
  background: var(--surface-soft); color: var(--muted);
  font-size: 11px; font-weight: 800;
  display: inline-flex; align-items: center; justify-content: center;
}
.rank-no-1 { background: linear-gradient(135deg, #f2c14e, #e09a2e); color: #fff; }
.rank-no-2 { background: linear-gradient(135deg, #d7dbe0, #aeb4bd); color: #fff; }
.rank-no-3 { background: linear-gradient(135deg, #d9a97f, #c77a45); color: #fff; }
.rank-thumb {
  flex: 0 0 38px; height: 38px; border-radius: 10px;
  background: linear-gradient(145deg, var(--brand-soft), var(--surface-soft));
  display: inline-flex; align-items: center; justify-content: center; font-size: 20px;
}
.rank-mid { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.rank-name { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-sub { font-size: 11px; color: var(--muted); }
.rank-price { font-size: 13px; font-weight: 800; color: var(--hot); white-space: nowrap; }
.recent li { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px dashed var(--line); }
.recent .rank-name { flex: 1; }

/* ---------- 最近摇到（移动端横滑） ---------- */
.recent-rail { display: none; }
.rail-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin: 4px 0 8px; }
.rail-head h2 { font-family: var(--font-hand); font-size: 16px; font-weight: 700; }
.rail-head span { font-size: 11px; color: var(--muted); }
.rail { list-style: none; margin: 0; padding: 4px 0 8px; display: flex; gap: 10px; overflow-x: auto; scroll-snap-type: x proximity; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
.rail::-webkit-scrollbar { display: none; }
.rail-item {
  flex: 0 0 auto; width: 132px; scroll-snap-align: start;
  display: flex; flex-direction: column; gap: 4px; padding: 10px 12px;
  border-radius: 12px; background: var(--surface); border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  animation: rise var(--rise-dur) var(--ease-back) both;
  animation-delay: calc(var(--i, 0) * 60ms);
}
.rail-emoji { font-size: 24px; line-height: 1; }
.rail-name { font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rail-price { font-size: 12px; font-weight: 800; color: var(--hot); }

@media (max-width: 820px) {
  .frame-body { min-height: 176px; padding: 28px 22px; }
  .banner-copy { max-width: 90%; }
  .banner-copy h1 { font-size: 26px; }
  .banner-copy > p { font-size: 13px; }
  .banner-points { margin-top: 14px; gap: 6px 12px; }
  .banner-points span { font-size: 11px; }
  .sticker-cup { font-size: 26px; right: 16px; }
  .sticker-cake { font-size: 24px; left: 14px; }
  .category-nav { padding: 14px 4px; gap: 0; }
  .category-icon { width: 46px; height: 46px; font-size: 22px; border-radius: 14px; }
  .category-label { font-size: 11px; }
  .home-grid { grid-template-columns: 1fr; }
  .draw-card { padding: 16px; }
  .result { gap: 12px; padding: 14px; }
  .result-pic { flex-basis: 100px; height: 100px; }
  .result-emoji { font-size: 56px; }
  .result-name { font-size: 19px; }
  .result-bottom { flex-wrap: wrap; }
  .price-wrap .price { font-size: 27px; }
  .result-actions { width: 100%; justify-content: flex-end; }
  .roll-btn { font-size: 16px; }
  .recent-rail { display: block; }
  .recent-rail .rail { margin: 0 -14px; padding: 4px 14px 8px; }
  .side-recent { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .slot.rolling, .slot.rolling::before, .slot.rolling::after,
  .roll-btn, .roll-icon, .live-badge i, .rise, .rail-item {
    animation: none;
  }
  .confetti { display: none; }
  .reveal-enter-active, .reveal-leave-active { transition: opacity var(--dur-fast) linear; }
  .reveal-enter-from, .reveal-leave-to { opacity: 0; transform: none; filter: none; }
}
</style>
