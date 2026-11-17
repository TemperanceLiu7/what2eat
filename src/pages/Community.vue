<script setup>
import { onMounted, ref } from 'vue'
import { fmtTime } from '@/data/db'
import { loadCheckins } from '@/stores/app'
import { toast } from '@/composables/useToast'

const latest = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const list = await loadCheckins()
    latest.value = list.slice(0, 3)
  } catch (err) {
    toast(err?.message || '社区内容加载失败')
  } finally {
    loading.value = false
  }
})

const entries = [
  {
    to: '/checkin',
    title: '打卡广场',
    desc: '看看同学们今天吃什么',
    tone: 'brand',
  },
  {
    to: '/vote',
    title: '投票广场',
    desc: '吃不吃？让大家投',
    tone: 'warm',
  },
]
</script>

<template>
  <div class="page community">
    <section class="head">
      <p class="kicker">社区板块</p>
      <h1>看看大家都在吃什么</h1>
      <p class="sub">只展示公开打卡；你自己的私密记录只在「个人」里，这里看不到。</p>
    </section>

    <section class="entries">
      <router-link v-for="e in entries" :key="e.to" :to="e.to" class="entry card" :class="e.tone">
        <span class="entry-body">
          <span class="entry-title">{{ e.title }}</span>
          <span class="entry-desc">{{ e.desc }}</span>
        </span>
        <span class="entry-arrow">→</span>
      </router-link>
    </section>

    <section class="block">
      <div class="section-head">
        <h2>最新公开打卡</h2>
        <router-link to="/checkin" class="more">全部 →</router-link>
      </div>

      <div v-if="loading" class="card empty">加载中…</div>
      <div v-else-if="!latest.length" class="card empty">
        还没有人公开发布，你可以去当第一个
      </div>

      <article v-for="c in latest" :key="c.id" class="card item">
        <img v-if="c.image" :src="c.image" class="thumb" alt="" />
        <div class="item-body">
          <div class="item-head">
            <span class="who">{{ c.who }}</span>
            <span class="muted">{{ fmtTime(c.at) }}</span>
          </div>
          <p class="text">{{ c.content }}</p>
          <span v-if="c.dishName" class="tag">{{ c.dishName }}</span>
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
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--muted);
  margin-bottom: 8px;
  text-transform: uppercase;
}

h1 {
  font-size: 26px;
}

.sub {
  margin-top: 8px;
  font-size: 14px;
  color: var(--muted);
}

.entries {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 16px 16px;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color var(--dur-fast) var(--ease-out);
}

.entry::before {
  content: '';
  position: absolute;
  top: -7px;
  left: 24px;
  width: 52px;
  height: 13px;
  transform: rotate(3deg);
  background: color-mix(in srgb, var(--leaf) 45%, transparent);
  border-left: 1px dashed rgba(255, 255, 255, 0.5);
  border-right: 1px dashed rgba(255, 255, 255, 0.5);
  border-radius: 2px;
}

.entry:nth-child(odd) {
  transform: rotate(0.9deg);
}

.entry:nth-child(even) {
  transform: rotate(-1deg);
}

.entry:hover {
  border-color: var(--ink-quiet);
}

.entry-emoji {
  font-size: 26px;
}

.entry-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.entry-title {
  font-size: 15px;
  font-weight: 600;
}

.entry-desc {
  font-size: 12px;
  color: var(--muted);
}

.entry-arrow {
  margin-left: auto;
  color: var(--brand);
}

.entry.brand {
  background: linear-gradient(135deg, var(--brand-soft), var(--surface));
}
.entry.warm {
  background: linear-gradient(135deg, var(--brand-line-soft), var(--surface));
}

.more {
  font-size: 12px;
  color: var(--brand);
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
  border-radius: var(--radius-md);
  object-fit: cover;
  flex-shrink: 0;
}

.item-body {
  min-width: 0;
  flex: 1;
}

.item-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}

.who {
  font-weight: 600;
}

.text {
  margin-top: 6px;
  font-size: 13px;
  color: var(--ink-soft);
}

.tag {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  padding: 3px 9px;
  border-radius: var(--radius-sm);
  background: var(--brand-soft);
  color: var(--brand);
}

@media (max-width: 820px) {
  h1 {
    font-size: 22px;
  }
  .entries {
    grid-template-columns: 1fr;
  }
}
</style>
