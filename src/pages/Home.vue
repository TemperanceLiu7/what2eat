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
  await sleep(520)
  const picked = pickRandom(source.value)
  dish.value = picked
  rolling.value = false
  if (picked) recordEaten(picked.id)
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
        <div class="slot" :class="{ rolling }">
          <Transition name="pop" mode="out-in">
            <div v-if="dish" :key="dish.id" class="slot-inner">
              <div class="slot-emoji">{{ dish.emoji }}</div>
              <h2 class="slot-name">{{ dish.name }}</h2>
              <p class="slot-shop">{{ dish.shop.emoji }} {{ dish.shop.name }}</p>
              <p class="slot-loc">{{ dish.shop.location }}</p>

              <div class="slot-meta">
                <span class="price">¥{{ dish.price }}</span>
                <span class="tag">{{ dish.category }}</span>
                <span class="tag">{{ dish.sourceLabel }}</span>
                <span class="heat">🔥 {{ heat }}</span>
              </div>

              <p class="slot-desc">{{ dish.desc }}</p>
            </div>

            <div v-else key="empty" class="slot-inner slot-empty">
              <div class="slot-emoji">🍽️</div>
              <p class="slot-name">还没摇</p>
              <p class="slot-loc">选好上面的范围，点按钮开始</p>
            </div>
          </Transition>
        </div>

        <UButton class="shake-btn" type="primary" size="large" block @click="roll">
          {{ dish ? '再摇一次' : '摇一摇' }}
        </UButton>

        <p class="hint">
          <template v-if="isMobile">可以直接甩动手机抽签，也可以点按钮。</template>
          <template v-else>点按钮开始，热度高的菜会被加权抽中。</template>
          当前范围：<b>{{ SOURCES.find((s) => s.key === source).label }}</b>
        </p>

        <div v-if="dish" class="result-actions">
          <UButton plain @click="fav">{{ faved ? '已收藏' : '收藏' }}</UButton>
          <UButton plain @click="like">{{ liked ? '已点赞' : '点赞' }}</UButton>
          <UButton plain @click="router.push('/checkin')">去打卡</UButton>
        </div>
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

        <section v-if="recent.length" class="side-card card">
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
.hero {
  padding: 8px 0 22px;
}

.hero-kicker {
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--brand);
  font-weight: 600;
  margin-bottom: 8px;
}

.hero h1 {
  font-size: 34px;
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.hero-sub {
  margin-top: 10px;
  color: var(--muted);
  font-size: 14px;
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

.slot {
  border-radius: 16px;
  background: linear-gradient(160deg, #fff8f3 0%, #fffdfa 55%, #fff 100%);
  border: 1px solid #ffe7d9;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
  overflow: hidden;
}

.slot-inner {
  text-align: center;
  padding: 28px 20px;
  width: 100%;
}

.slot.rolling .slot-inner {
  animation: wobble 0.55s ease-in-out;
}

@keyframes wobble {
  0% {
    transform: rotate(0) scale(1);
  }
  20% {
    transform: rotate(-6deg) scale(1.05);
  }
  40% {
    transform: rotate(5deg) scale(1.07);
  }
  60% {
    transform: rotate(-4deg) scale(1.03);
  }
  80% {
    transform: rotate(3deg) scale(1.02);
  }
  100% {
    transform: rotate(0) scale(1);
  }
}

.slot-emoji {
  font-size: 62px;
  line-height: 1;
  margin-bottom: 14px;
  filter: drop-shadow(0 8px 14px rgba(255, 122, 69, 0.22));
}

.slot-name {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.slot-shop {
  margin-top: 10px;
  font-size: 14px;
  color: #4a5160;
}

.slot-loc {
  margin-top: 4px;
  font-size: 12px;
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
  font-size: 18px;
  font-weight: 700;
  color: var(--brand);
}

.tag {
  font-size: 12px;
  padding: 3px 9px;
  border-radius: 999px;
  background: #f3f4f7;
  color: #4a5160;
}

.heat {
  font-size: 12px;
  color: #b0752f;
}

.slot-desc {
  margin-top: 12px;
  font-size: 13px;
  color: var(--muted);
}

.slot-empty .slot-name {
  color: #6b7280;
  font-weight: 600;
}

.shake-btn {
  font-weight: 600;
  letter-spacing: 0.04em;
  max-width: 320px;
  margin: 0 auto;
}

.hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
}

.result-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  justify-content: center;
}

.side {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  font-size: 14px;
}

.rank li:last-child,
.recent li:last-child {
  border-bottom: none;
}

.no {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: #f3f4f7;
  color: #8a9099;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.no-1 {
  background: #ff7a45;
  color: #fff;
}
.no-2 {
  background: #ffb020;
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
  font-size: 12px;
  color: var(--muted);
}

.pop-enter-active,
.pop-leave-active {
  transition: all 0.18s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

@media (max-width: 820px) {
  .hero {
    padding: 4px 0 16px;
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
}
</style>
