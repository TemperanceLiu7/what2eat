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
    <section class="hero">
      <h1>今天吃什么</h1>
      <p class="hero-sub">按来源筛一下，抽一道。抽到的会写进「最近」，不会连着重复。</p>
    </section>

    <div class="source-bar">
      <button
        v-for="s in SOURCES"
        :key="s.key"
        class="chip"
        :class="{ active: source === s.key }"
        @click="source = s.key"
      >
        {{ s.label }}
      </button>
    </div>

    <div class="home-grid">
      <section class="draw card">
        <div class="slot" :class="{ rolling }" :aria-busy="rolling" aria-live="polite">
          <span class="slot-frame" aria-hidden="true"></span>

          <div v-if="rolling" key="rolling" class="slot-inner slot-wait">
            <p class="slot-name slot-name--quiet">抽签中</p>
          </div>

          <div v-else-if="dish" :key="`${dish.id}-${drawSeq}`" class="slot-inner slot-dish">
              <p class="slot-no num">第 {{ drawSeq }} 次</p>
              <h2 class="slot-name">{{ dish.name }}</h2>
              <p class="slot-shop">{{ dish.shop.name }}</p>
              <p class="slot-loc">{{ dish.shop.location }}</p>

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
}

.hero {
  padding: var(--space-4) 0 18px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 18px;
}

.hero h1 {
  font-size: var(--fs-2xl);
  line-height: 1.2;
}

.hero-sub {
  margin-top: 8px;
  color: var(--muted);
  font-size: var(--fs-sm);
  line-height: 1.7;
  max-width: 46em;
}

.source-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

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
  .hero h1 {
    font-size: 24px;
  }
  .source-bar {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 4px;
    margin-bottom: 14px;
    scrollbar-width: none;
  }
  .source-bar::-webkit-scrollbar {
    display: none;
  }
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
