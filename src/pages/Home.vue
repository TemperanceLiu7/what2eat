<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  SOURCES,
  allDishViews,
  heatOf,
  pickRandom,
  recordEaten,
  isLiked,
  isFaved,
  toggleLike,
  toggleFavorite,
  state,
} from '@/data/db'
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

const liked = computed(() => !!dish.value && isLiked(dish.value.id))
const faved = computed(() => !!dish.value && isFaved(dish.value.id))
const heat = computed(() => (dish.value ? heatOf(dish.value) : 0))

const hot = computed(() =>
  allDishViews()
    .map((d) => ({ ...d, heat: heatOf(d) }))
    .sort((a, b) => b.heat - a.heat)
    .slice(0, 5),
)

const recent = computed(() =>
  state.eaten
    .slice(0, 3)
    .map((e) => allDishViews().find((d) => d.id === e.dishId))
    .filter(Boolean),
)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function roll() {
  if (rolling.value) return
  enableShake() // 顺便申请动作权限：iOS 必须放在用户手势里
  if (navigator.vibrate) navigator.vibrate(15)

  rolling.value = true
  await sleep(520) // 与 CSS 里的 --draw-dur 对齐
  const picked = pickRandom(source.value)
  dish.value = picked
  drawSeq.value += 1
  rolling.value = false
  if (picked) recordEaten(picked.id)
  if (navigator.vibrate) navigator.vibrate(8) // 结果落定时补一次轻震
}

function like() {
  if (!dish.value) return
  const on = toggleLike(dish.value.id)
  toast(on ? '已点赞，会略微提高它的中签率' : '已取消点赞')
}

function fav() {
  if (!dish.value) return
  const on = toggleFavorite(dish.value.id)
  toast(on ? '已收藏，去「我的」查看' : '已取消收藏')
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
      <p class="hero-kicker">校园 · 今天吃什么</p>
      <h1>别纠结了，交给随机</h1>
      <p class="hero-sub">食堂、外卖、饭店、夜市，选个范围摇一个，摇到就吃。</p>
    </section>

    <div class="source-bar">
      <button
        v-for="s in SOURCES"
        :key="s.key"
        class="chip"
        :class="{ active: source === s.key }"
        @click="source = s.key"
      >
        <span>{{ s.emoji }}</span>{{ s.label }}
      </button>
    </div>

    <div class="home-grid">
      <section class="draw card">
        <div class="slot" :class="{ rolling }" :aria-busy="rolling" aria-live="polite">
          <Transition name="reveal" mode="out-in">
            <div v-if="dish" :key="`${dish.id}-${drawSeq}`" class="slot-inner">
              <div class="slot-emoji rise" style="--d: 0ms">{{ dish.emoji }}</div>
              <h2 class="slot-name rise" style="--d: 60ms">{{ dish.name }}</h2>
              <p class="slot-shop rise" style="--d: 110ms">
                {{ dish.shop.emoji }} {{ dish.shop.name }}
              </p>
              <p class="slot-loc rise" style="--d: 130ms">{{ dish.shop.location }}</p>

              <div class="slot-meta">
                <span class="price rise" style="--d: 180ms">¥{{ dish.price }}</span>
                <span class="tag rise" style="--d: 210ms">{{ dish.category }}</span>
                <span class="tag rise" style="--d: 235ms">{{ dish.sourceLabel }}</span>
                <span class="heat rise" style="--d: 265ms">🔥 {{ heat }}</span>
              </div>

              <p class="slot-desc rise" style="--d: 300ms">{{ dish.desc }}</p>
            </div>

            <div v-else key="empty" class="slot-inner slot-empty">
              <div class="slot-emoji">🍽️</div>
              <p class="slot-name">还没摇</p>
              <p class="slot-loc">选好上面的范围，点按钮开始</p>
            </div>
          </Transition>
        </div>

        <UButton
          class="shake-btn"
          :class="{ 'is-rolling': rolling }"
          type="primary"
          size="large"
          block
          @click="roll"
        >
          {{ rolling ? '正在摇…' : dish ? '再摇一次' : '摇一摇' }}
        </UButton>

        <p class="hint">
          <template v-if="isMobile">可以直接甩动手机抽签，也可以点按钮。</template>
          <template v-else>点按钮开始，热度高的菜会被加权抽中。</template>
          当前范围：<b>{{ SOURCES.find((s) => s.key === source).label }}</b>
        </p>

        <div v-if="dish" class="result-actions rise" style="--d: 340ms">
          <UButton plain @click="fav">{{ faved ? '已收藏' : '收藏' }}</UButton>
          <UButton plain @click="like">{{ liked ? '已点赞' : '点赞' }}</UButton>
          <UButton plain @click="router.push('/checkin')">去打卡</UButton>
        </div>
      </section>

      <!-- 移动端专属：最近抽到（横向滑动，桌面隐藏） -->
      <section v-if="recent.length" class="recent-rail">
        <div class="section-head">
          <h2>最近抽到</h2>
          <span class="sub">已自动避开</span>
        </div>
        <ul class="rail">
          <li
            v-for="(d, i) in recent"
            :key="d.id"
            class="rail-item"
            :style="{ '--i': i }"
          >
            <span class="rail-emoji">{{ d.emoji }}</span>
            <span class="rail-name">{{ d.name }}</span>
            <span class="rail-price">¥{{ d.price }}</span>
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
              <span class="no" :class="`no-${i + 1}`">{{ i + 1 }}</span>
              <span class="rank-emoji">{{ d.emoji }}</span>
              <span class="rank-name">{{ d.name }}</span>
              <span class="rank-heat">{{ d.heat }}</span>
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
              <span class="rank-emoji">{{ d.emoji }}</span>
              <span class="rank-name">{{ d.name }}</span>
              <span class="rank-heat">{{ d.price }} 元</span>
            </li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
/* 首页动效节奏：抽签 520ms，和 roll() 里的等待严格对齐 */
.home {
  --draw-dur: 0.52s;
  --draw-enter: 0.44s;
  --rise-dur: 0.38s;
}

.hero {
  padding: var(--space-8) 0 22px;
}

.hero-kicker {
  font-size: var(--fs-xs);
  letter-spacing: 0.12em;
  color: var(--brand);
  font-weight: 600;
  margin-bottom: var(--space-8);
}

.hero h1 {
  font-size: var(--fs-2xl);
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.hero-sub {
  margin-top: 10px;
  color: var(--muted);
  font-size: var(--fs-base);
}

.source-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.85fr);
  gap: 20px;
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

/* ---------- 摇签舞台 ---------- */

.slot {
  position: relative;
  isolation: isolate;
  border-radius: 16px;
  background: var(--surface-warm);
  background-size: 180% 180%;
  border: 1px solid var(--brand-line-soft);
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
  overflow: hidden;
}

/* 主色光晕：抽签时呼吸一次 */
.slot::before {
  content: '';
  position: absolute;
  inset: -18%;
  z-index: 0;
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(circle at 50% 46%, var(--brand-glow) 0%, transparent 62%);
}

/* 扫光：一块高光从左刷到右，给「抽」一个方向感 */
.slot::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  opacity: 0;
  transform: translateX(-120%);
  background: linear-gradient(
    105deg,
    transparent 32%,
    rgba(255, 255, 255, 0.72) 48%,
    transparent 64%
  );
}

/* 背景色块缓慢流动，营造「在抽」的不稳定感 */
.slot.rolling {
  animation: slot-flow var(--draw-dur) var(--ease-out) both;
}

.slot.rolling::before {
  animation: aura-pulse var(--draw-dur) var(--ease-out) both;
}

.slot.rolling::after {
  animation: sheen-sweep var(--draw-dur) var(--ease-out) both;
}

@keyframes slot-flow {
  0% {
    background-position: 0% 50%;
  }
  55% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

@keyframes aura-pulse {
  0% {
    opacity: 0;
    transform: scale(0.9);
  }
  35% {
    opacity: 0.9;
    transform: scale(1);
  }
  70% {
    opacity: 0.45;
    transform: scale(1.06);
  }
  100% {
    opacity: 0;
    transform: scale(1.02);
  }
}

@keyframes sheen-sweep {
  0% {
    opacity: 0;
    transform: translateX(-120%);
  }
  20% {
    opacity: 1;
  }
  70% {
    opacity: 0.9;
    transform: translateX(120%);
  }
  100% {
    opacity: 0;
    transform: translateX(120%);
  }
}

.slot-inner {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 28px 20px;
  width: 100%;
}

/* 抽签中的节奏：三下「心跳」，缩放 + 模糊 + 微旋转，不只是放大缩小 */
.slot.rolling .slot-inner {
  animation: draw-beat var(--draw-dur) var(--ease-out) both;
}

@keyframes draw-beat {
  0% {
    transform: scale(1) rotate(0);
    filter: blur(0);
  }
  16% {
    transform: scale(1.05) rotate(-1.2deg);
    filter: blur(2.4px);
  }
  34% {
    transform: scale(1.01) rotate(0.6deg);
    filter: blur(0.8px);
  }
  52% {
    transform: scale(1.06) rotate(1deg);
    filter: blur(2.8px);
  }
  70% {
    transform: scale(1.02) rotate(-0.6deg);
    filter: blur(1px);
  }
  86% {
    transform: scale(1.045) rotate(0.4deg);
    filter: blur(1.8px);
  }
  100% {
    transform: scale(1) rotate(0);
    filter: blur(0);
  }
}

/* emoji 用不同频率翻转，和卡片的节拍错开，制造层次 */
.slot.rolling .slot-emoji {
  animation: emoji-tumble var(--draw-dur) var(--ease-out) both;
}

@keyframes emoji-tumble {
  0% {
    transform: rotate(0) scale(1);
  }
  25% {
    transform: rotate(-16deg) scale(1.14);
  }
  50% {
    transform: rotate(12deg) scale(0.94);
  }
  75% {
    transform: rotate(-9deg) scale(1.1);
  }
  100% {
    transform: rotate(0) scale(1);
  }
}

/* ---------- 结果入场：位移 + 淡入 + 轻微回弹 ---------- */

.reveal-enter-active {
  transition:
    opacity 0.26s var(--ease-out),
    transform var(--draw-enter) var(--ease-back),
    filter var(--draw-enter) var(--ease-out);
}

.reveal-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.2s ease,
    filter 0.2s ease;
}

.reveal-enter-from {
  opacity: 0;
  transform: translateY(18px) scale(0.94);
  filter: blur(7px);
}

/* 离场时「糊掉再消失」，避免抽签结束那一帧从模糊直接跳回清晰 */
.reveal-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
  filter: blur(5px);
}

/* 关键信息错峰出现：菜名 → 价格 → 热度 */
.rise {
  animation: rise var(--rise-dur) var(--ease-back) both;
  animation-delay: var(--d, 0ms);
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.slot-emoji {
  font-size: 62px;
  line-height: 1;
  margin-bottom: 14px;
  filter: drop-shadow(0 8px 14px var(--brand-glow));
}

.slot-name {
  font-size: var(--fs-xl);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.slot-shop {
  margin-top: 10px;
  font-size: var(--fs-base);
  color: var(--ink-soft);
}

.slot-loc {
  margin-top: var(--space-4);
  font-size: var(--fs-xs);
  color: var(--muted);
}

.slot-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.price {
  font-size: var(--fs-lg);
  font-weight: 700;
  color: var(--brand);
}

.tag {
  font-size: var(--fs-xs);
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  background: var(--surface-soft);
  color: var(--ink-soft);
}

.heat {
  font-size: var(--fs-xs);
  color: var(--brand-2-deep);
}

.slot-desc {
  margin-top: var(--space-12);
  font-size: var(--fs-sm);
  color: var(--muted);
}

.slot-empty .slot-name {
  color: var(--ink-quiet);
  font-weight: 600;
}

.shake-btn {
  font-weight: 600;
  letter-spacing: 0.04em;
  max-width: 320px;
  margin: 0 auto;
  transition: transform var(--dur-fast) var(--ease-out);
}

/* 按钮跟抽签一起呼吸，但幅度比卡片小，形成主次 */
.shake-btn.is-rolling {
  animation: btn-pulse var(--draw-dur) var(--ease-out) both;
}

@keyframes btn-pulse {
  0% {
    box-shadow: 0 0 0 0 var(--brand-glow);
    transform: scale(1);
  }
  22% {
    box-shadow: 0 0 0 10px rgba(255, 122, 69, 0);
    transform: scale(0.985);
  }
  50% {
    box-shadow: 0 0 0 0 var(--brand-glow);
    transform: scale(1.015);
  }
  78% {
    box-shadow: 0 0 0 8px rgba(255, 122, 69, 0);
    transform: scale(0.995);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(255, 122, 69, 0);
    transform: scale(1);
  }
}

.hint {
  margin-top: var(--space-12);
  font-size: var(--fs-xs);
  color: var(--muted);
  text-align: center;
}

.result-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  justify-content: center;
}

/* ---------- 侧栏 ---------- */

.side {
  display: flex;
  flex-direction: column;
  gap: var(--space-16);
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
  padding: 9px 0;
  border-bottom: 1px dashed var(--line);
  font-size: var(--fs-base);
}

.rank li:last-child,
.recent li:last-child {
  border-bottom: none;
}

.no {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: var(--surface-soft);
  color: var(--muted);
  font-size: var(--fs-xs);
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.no-1 {
  background: var(--brand);
  color: #fff;
}
.no-2 {
  background: var(--brand-2);
  color: #fff;
}
.no-3 {
  background: #ffd08a;
  color: #8a5a00;
}

.rank-emoji {
  font-size: 17px;
}

.rank-name {
  flex: 1;
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
  gap: 10px;
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
  width: 128px;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  animation: rise var(--draw-enter) var(--ease-back) both;
  animation-delay: calc(var(--i, 0) * 60ms);
}

.rail-emoji {
  font-size: 24px;
  line-height: 1;
}

.rail-name {
  font-size: var(--fs-sm);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rail-price {
  font-size: var(--fs-xs);
  font-weight: 700;
  color: var(--brand);
}

@media (max-width: 820px) {
  .hero {
    padding: var(--space-4) 0 var(--space-16);
  }
  .hero h1 {
    font-size: 26px;
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
    min-height: 280px;
  }
  .shake-btn {
    max-width: none;
  }
  .slot-emoji {
    font-size: 52px;
  }
  .slot-name {
    font-size: 22px;
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

/* ---------- 减少动效：退化为基础淡入 ---------- */
@media (prefers-reduced-motion: reduce) {
  .slot.rolling,
  .slot.rolling::before,
  .slot.rolling::after,
  .slot.rolling .slot-inner,
  .slot.rolling .slot-emoji,
  .shake-btn.is-rolling {
    animation: none;
  }

  .slot.rolling::before,
  .slot.rolling::after {
    opacity: 0;
  }

  .slot.rolling .slot-inner {
    filter: none;
    transform: none;
  }

  .rise,
  .rail-item {
    animation: none;
  }

  .reveal-enter-active,
  .reveal-leave-active {
    transition: opacity var(--dur-fast) linear;
  }

  .reveal-enter-from,
  .reveal-leave-to {
    opacity: 0;
    transform: none;
    filter: none;
  }
}
</style>
