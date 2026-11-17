<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { SOURCES, allDishViews, heatOf, isLiked, isFaved } from '@/data/db'
import { pickRandom, toggleFavorite, toggleLike } from '@/api'
import { pushEaten, ui } from '@/stores/app'
import { toast } from '@/composables/useToast'
import { useIsMobile } from '@/composables/useIsMobile'
import UButton from '@/ui/UButton.vue'

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

/** 真接口会带 liked / favorited，mock 从本地记录里取 */
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
  enableShake() // 顺便申请动作权限：iOS 必须放在用户手势里
  if (navigator.vibrate) navigator.vibrate(15)

  rolling.value = true
  await sleep(520) // 与 CSS 里的 --draw-dur 对齐
  try {
    const picked = await pickRandom(source.value)
    dish.value = picked
    drawSeq.value += 1
    syncFlags(picked)
    if (picked) pushEaten(picked)
    if (picked) burstConfetti()
  } catch (err) {
    toast(err?.message || '抽签失败，稍后再试')
  } finally {
    rolling.value = false
  }
  if (navigator.vibrate) navigator.vibrate(8) // 结果落定时补一次轻震
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

// ---- 手机甩动抽签（HTTPS 下才可用，按钮始终兜底） ----
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
      <section class="draw card">
        <div class="slot" :class="{ rolling }" :aria-busy="rolling" aria-live="polite">
          <span class="slot-frame" aria-hidden="true"></span>
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

          <div v-if="rolling" key="rolling" class="slot-inner slot-wait">
            <p class="slot-name slot-name--quiet">抽签中</p>
          </div>

          <div v-else-if="dish" :key="`${dish.id}-${drawSeq}`" class="slot-inner slot-dish">
              <p class="slot-no num">第 {{ drawSeq }} 次</p>
              <h2 class="slot-name">{{ dish.name }}</h2>
              <p class="slot-shop">{{ dish.shop?.name }}</p>
              <p class="slot-loc">{{ dish.shop?.location }}</p>

              <ul class="slot-meta">
                <li class="price num">¥{{ dish.price }}</li>
                <li>{{ dish.category }}</li>
                <li>{{ dish.sourceLabel }}</li>
                <li class="heat">热度 <span class="num">{{ heat }}</span></li>
              </ul>

              <p class="slot-desc">{{ dish.desc }}</p>
            </div>

          <div v-else key="empty" class="slot-inner slot-wait">
            <p class="slot-name slot-name--quiet">还没抽</p>
            <p class="slot-loc">上面选好范围，点下面的按钮</p>
          </div>
        </div>

        <UButton
          class="shake-btn"
          type="primary"
          size="large"
          block
          :disabled="rolling"
          @click="roll"
        >
          {{ rolling ? '抽签中…' : dish ? '再抽一道' : '抽一道' }}
        </UButton>

        <p class="hint">
          <template v-if="isMobile">也可以直接甩动手机。</template>
          <template v-else>热度高的菜权重略高。</template>
          当前范围
          <b>{{ SOURCES.find((s) => s.key === source).label }}</b>
        </p>

        <div v-if="dish" class="result-actions">
          <UButton plain size="small" @click="fav">{{ faved ? '已收藏' : '收藏' }}</UButton>
          <UButton plain size="small" @click="like">{{ liked ? '已点赞' : '点赞' }}</UButton>
          <UButton plain size="small" @click="router.push('/checkin')">去打卡</UButton>
        </div>
      </section>

      <!-- 移动端专属：最近抽到（横向滑动，桌面隐藏） -->
      <section v-if="recent.length" class="recent-rail">
        <div class="section-head">
          <h2>最近抽到</h2>
          <span class="sub">已自动避开</span>
        </div>
        <ul class="rail">
          <li v-for="(d, i) in recent" :key="d.id" class="rail-item" :style="{ '--i': i }">
            <span class="rail-name">{{ d.name }}</span>
            <span class="rail-price num">¥{{ d.price }}</span>
          </li>
        </ul>
      </section>

      <aside class="side">
        <section class="side-card card">
          <div class="section-head">
            <h2>本周人气</h2>
            <span class="sub">点赞 + 收藏</span>
          </div>
          <ul class="rank">
            <li v-for="(d, i) in hot" :key="d.id">
              <span class="no num" :class="{ 'no-top': i === 0 }">{{ i + 1 }}</span>
              <span class="rank-name">{{ d.name }}</span>
              <span class="rank-heat num">{{ d.heat }}</span>
            </li>
          </ul>
        </section>

        <section v-if="recent.length" class="side-card card side-recent">
          <div class="section-head">
            <h2>最近摇到</h2>
            <span class="sub">已自动避开</span>
          </div>
          <ul class="recent">
            <li v-for="d in recent" :key="d.id">
              <span class="rank-name">{{ d.name }}</span>
              <span class="rank-heat num">{{ d.price }} 元</span>
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
  grid-template-columns: minmax(0, 1.55fr) minmax(260px, 0.85fr);
  gap: 18px;
  align-items: start;
}

.draw {
  display: flex;
  flex-direction: column;
}

/* 横向滑动的子项会把 grid 的自动最小尺寸撑大，必须显式归零，否则整页横向溢出 */
.draw,
.recent-rail {
  min-width: 0;
}

/* ---------- 抽签面板：一张菜单卡 ---------- */

.slot {
  position: relative;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--surface);
  min-height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  overflow: hidden;
}

/* 内圈虚线：食堂贴纸/菜单牌的那种框，比阴影便宜也更好看 */
.slot-frame {
  position: absolute;
  inset: 9px;
  border: 1px dashed var(--line);
  border-radius: 2px;
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

.slot.rolling .slot-frame {
  border-color: var(--brand-line);
}

.slot-inner {
  position: relative;
  text-align: center;
  padding: 30px 22px;
  width: 100%;
}

.slot-no {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 10px;
}

.slot-name {
  font-size: var(--fs-xl);
  font-family: var(--font-serif);
  font-weight: 600;
  line-height: 1.35;
}

.slot-name--quiet {
  color: var(--ink-quiet);
  font-weight: 400;
}

.slot-shop {
  margin-top: 10px;
  font-size: var(--fs-base);
  color: var(--ink-soft);
}

.slot-loc {
  margin-top: 4px;
  font-size: var(--fs-xs);
  color: var(--muted);
}

/* 元信息用一行"·"分隔的文字，而不是一排彩色胶囊 */
.slot-meta {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: center;
  gap: 0;
  margin: 14px 0 0;
  padding: 0;
  font-size: var(--fs-xs);
  color: var(--ink-soft);
}

.slot-meta li + li::before {
  content: '·';
  margin: 0 9px;
  color: var(--muted);
}

.price {
  font-size: var(--fs-md);
  color: var(--brand);
}

.heat {
  color: var(--muted);
}

.slot-desc {
  margin-top: 14px;
  font-size: var(--fs-sm);
  color: var(--muted);
  line-height: 1.7;
  max-width: 34em;
  margin-left: auto;
  margin-right: auto;
}

/* 结果入场：一次性淡入 + 4px 位移，不做离场动画（避免 out-in 卡住新内容） */
.slot-dish {
  animation: slot-in 0.18s var(--ease-out);
}

.slot-wait {
  animation: slot-in 0.12s linear;
}

/* 只动位置不动透明度：动画被节流时内容依然可见，不会出现"空卡片" */
@keyframes slot-in {
  from {
    transform: translateY(4px);
  }
  to {
    transform: translateY(0);
  }
}

.shake-btn {
  max-width: 320px;
  margin: 0 auto;
}

.hint {
  margin-top: 12px;
  font-size: var(--fs-xs);
  color: var(--muted);
  text-align: center;
}

.hint b {
  color: var(--ink-soft);
  font-weight: 600;
}

.result-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  justify-content: center;
}

/* ---------- 侧栏 ---------- */

.side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rank,
.recent {
  list-style: none;
  margin: 0;
  padding: 0;
}

.rank li,
.recent li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
  font-size: var(--fs-sm);
}

.rank li:last-child,
.recent li:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

/* 名次只用等宽数字，第一名给朱红，不再做彩色方块 */
.no {
  width: 16px;
  color: var(--muted);
  font-size: var(--fs-xs);
  flex-shrink: 0;
}

.no-top {
  color: var(--brand);
}

.rank-name {
  flex: 1;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-heat {
  font-size: var(--fs-xs);
  color: var(--muted);
}

/* ---------- 最近抽到（移动端横向滑动条） ---------- */

.recent-rail {
  display: none;
}

.rail {
  list-style: none;
  margin: 0;
  padding: var(--space-4) 0 var(--space-8);
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.rail::-webkit-scrollbar {
  display: none;
}
.rail-item {
  flex: 0 0 auto;
  width: 124px;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.rail-name {
  font-size: var(--fs-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rail-price {
  font-size: var(--fs-xs);
  color: var(--brand);
}

@media (max-width: 820px) {
  .frame-body { min-height: 176px; padding: 28px 22px; }
  .banner-copy { max-width: 90%; }
  .banner-copy h1 { font-size: 26px; }
  .banner-copy > p { font-size: 13px; }
  .banner-points { margin-top: 14px; gap: 6px 12px; }
  .banner-points span { font-size: 11px; }
  .sticker-cup { font-size: 26px; right: 16px; }
  .sticker-cake { font-size: 24px; left: 14px; }
  .confetti { display: none; }
  .category-nav { padding: 14px 4px; gap: 0; }
  .category-icon { width: 46px; height: 46px; font-size: 22px; border-radius: 14px; }
  .category-label { font-size: 11px; }
  .home-grid {
    grid-template-columns: 1fr;
  }
  .slot {
    min-height: 250px;
  }
  .shake-btn {
    max-width: none;
  }
  .slot-name {
    font-size: 20px;
  }
  .result-actions {
    justify-content: stretch;
  }
  .result-actions > * {
    flex: 1;
  }

  /* 移动端才显示横向条，并让两侧出血到屏幕边缘 */
  .recent-rail {
    display: block;
  }
  .recent-rail .rail {
    margin: 0 -14px;
    padding: var(--space-4) 14px var(--space-8);
  }
  /* 桌面侧栏那张「最近摇到」在手机上收起来，避免和横向条重复 */
  .side-recent {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .slot-dish,
  .slot-wait {
    animation: none;
  }
}
</style>
