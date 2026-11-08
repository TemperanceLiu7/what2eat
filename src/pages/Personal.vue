<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fmtTime } from '@/data/db'
import { isLoggedIn, loadCheckins, loadPreferences, ui } from '@/stores/app'
import { toast } from '@/composables/useToast'

const router = useRouter()
const loading = ref(false)

const pref = computed(() => ui.preferences || {})
const mine = computed(() => ui.checkins || [])

onMounted(async () => {
  if (!isLoggedIn.value) return
  loading.value = true
  try {
    await Promise.all([loadCheckins('mine'), loadPreferences()])
  } catch (err) {
    toast(err?.message || '加载失败')
  } finally {
    loading.value = false
  }
})

const entries = [
  {
    to: '/draw',
    emoji: '🎲',
    title: '摇一摇',
    desc: '不知道吃什么？随机一个',
    tone: 'brand',
  },
  {
    to: '/eat',
    emoji: '🍱',
    title: '今天吃了啥',
    desc: '拍照识别，记一笔口味',
    tone: 'warm',
  },
  {
    to: '/me',
    emoji: '⭐',
    title: '我的收藏',
    desc: '常吃的都在这里',
    tone: 'soft',
  },
]
</script>

<template>
  <div class="page personal">
    <section class="head">
      <p class="kicker">个人板块</p>
      <h1>{{ isLoggedIn ? (ui.user?.name || ui.user?.username || '同学') + '，吃点什么？' : '吃点什么？' }}</h1>
      <p class="sub">你自己的口味、记录和收藏都在这里，不需要进社区也能用。</p>
    </section>

    <!-- 未登录提示 -->
    <section v-if="!isLoggedIn" class="card notice">
      <div>
        <strong>还没登录</strong>
        <p>摇一摇不需要登录；记录「今天吃了啥」和攒口味偏好需要账号（并完成学号核验）。</p>
      </div>
      <router-link to="/login" class="inline-btn">去登录 →</router-link>
    </section>

    <!-- 入口卡 -->
    <section class="entries">
      <router-link
        v-for="e in entries"
        :key="e.to"
        :to="e.to"
        class="entry card"
        :class="e.tone"
      >
        <span class="entry-emoji">{{ e.emoji }}</span>
        <span class="entry-body">
          <span class="entry-title">{{ e.title }}</span>
          <span class="entry-desc">{{ e.desc }}</span>
        </span>
        <span class="entry-arrow">→</span>
      </router-link>
    </section>

    <!-- 偏好画像 -->
    <section v-if="isLoggedIn" class="card pref">
      <div class="section-head">
        <h2>我的口味</h2>
        <span class="sub">来自全部记录（含私密）</span>
      </div>

      <div class="stats">
        <div class="stat">
          <span class="value">{{ pref.totalCheckins ?? 0 }}</span>
          <span class="label">总记录</span>
        </div>
        <div class="stat">
          <span class="value">{{ pref.last7Days ?? 0 }}</span>
          <span class="label">近 7 天</span>
        </div>
        <div class="stat">
          <span class="value">{{ pref.privateCount ?? 0 }}</span>
          <span class="label">仅自己可见</span>
        </div>
      </div>

      <div v-if="(pref.topDishes || []).length" class="top">
        <span class="label">常吃</span>
        <div class="chips">
          <span v-for="d in pref.topDishes" :key="d.name" class="tag">
            {{ d.name }}<em>{{ d.count }}</em>
          </span>
        </div>
      </div>
      <div v-else class="empty-pref">
        还没有记录。点上面的「今天吃了啥」拍一张，这里就会慢慢长出你的口味。
      </div>
    </section>

    <!-- 我的记录 -->
    <section v-if="isLoggedIn" class="block">
      <div class="section-head">
        <h2>我的记录</h2>
        <span class="sub">{{ mine.length }} 条</span>
      </div>

      <div v-if="loading" class="card empty">加载中…</div>
      <div v-else-if="!mine.length" class="card empty">
        <span class="emoji">🍚</span>
        还没有记录，去「今天吃了啥」拍一张
      </div>

      <article v-for="c in mine" :key="c.id" class="card item">
        <img v-if="c.image" :src="c.image" class="thumb" alt="" />
        <div class="item-body">
          <div class="item-head">
            <span class="name">{{ c.dishName || c.content }}</span>
            <span v-if="c.visibility === 'private'" class="lock">🔒 仅自己</span>
          </div>
          <p class="muted">{{ c.who }} · {{ fmtTime(c.at) }}</p>
          <p v-if="c.content && c.dishName" class="text">{{ c.content }}</p>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.head {
  padding: 4px 0 18px;
}

.kicker {
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--brand);
  font-weight: 600;
  margin-bottom: 6px;
}

h1 {
  font-size: 26px;
}

.sub {
  margin-top: 8px;
  font-size: 14px;
  color: var(--muted);
}

.notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  border: 1px solid #ffe1d3;
  background: #fffaf6;
}

.notice p {
  margin-top: 4px;
  font-size: 13px;
  color: var(--muted);
}

:deep(.inline-btn) {
  color: var(--brand);
  font-size: 13px;
  white-space: nowrap;
}

.entries {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.entry {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.entry:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.entry-emoji {
  font-size: 24px;
}

.entry-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.entry-title {
  font-size: 14px;
  font-weight: 600;
}

.entry-desc {
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entry-arrow {
  margin-left: auto;
  color: var(--brand);
}

.entry.brand {
  background: linear-gradient(135deg, #fff4ee, #fff);
}
.entry.warm {
  background: linear-gradient(135deg, #fff8ec, #fff);
}
.entry.soft {
  background: linear-gradient(135deg, #f6f7fb, #fff);
}

.pref {
  margin-bottom: 18px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 12px 0;
}

.stat {
  background: #f7f8fa;
  border-radius: 12px;
  padding: 10px;
  text-align: center;
}

.stat .value {
  display: block;
  font-size: 20px;
  font-weight: 700;
}

.stat .label {
  font-size: 12px;
  color: var(--muted);
}

.top {
  margin-top: 6px;
}

.tag {
  display: inline-block;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #fff1ea;
  color: var(--brand);
}

.tag em {
  font-style: normal;
  margin-left: 4px;
  opacity: 0.7;
}

.empty-pref {
  margin-top: 8px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
}

.block {
  margin-top: 4px;
}

.item {
  display: flex;
  gap: 12px;
  padding: 12px;
  margin-bottom: 10px;
}

.thumb {
  width: 76px;
  height: 76px;
  border-radius: 10px;
  object-fit: cover;
  flex-shrink: 0;
}

.item-body {
  min-width: 0;
  flex: 1;
}

.item-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name {
  font-size: 14px;
  font-weight: 600;
}

.lock {
  font-size: 11px;
  color: #8a6a2f;
  background: #fdf7ec;
  border-radius: 999px;
  padding: 2px 8px;
}

.text {
  margin-top: 4px;
  font-size: 13px;
  color: #4a5160;
}

@media (max-width: 820px) {
  h1 {
    font-size: 22px;
  }
  .entries {
    grid-template-columns: 1fr;
  }
  .notice {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
