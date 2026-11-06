<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { state, createVote, castVote, simulateVotes, votesNeeded, voteStatusText, fmtTime } from '@/data/db'
import { toast } from '@/composables/useToast'
import UField from '@/ui/UField.vue'
import UButton from '@/ui/UButton.vue'
import UProgress from '@/ui/UProgress.vue'

const router = useRouter()

const title = ref('')
const target = ref('')
const targetCount = ref(6)
const openForm = ref(false)

const verified = computed(() => state.user.verified)
const pct = (v) => Math.min(100, Math.round(((v.agree || 0) / v.targetCount) * 100))
const remain = (v) => Math.max(0, votesNeeded(v.targetCount) - v.agree)

function submit() {
  const res = createVote({ title: title.value, target: target.value, targetCount: targetCount.value })
  if (!res.ok) {
    toast(res.message)
    if (res.code === 'UNVERIFIED') router.push('/me')
    return
  }
  toast('投票已发起，拉同学来投')
  title.value = ''
  target.value = ''
  targetCount.value = 6
  openForm.value = false
}

function vote(v, option) {
  if (option === 'agree' && !verified.value) {
    toast('参与投票需要先完成学号核验')
    return
  }
  const res = castVote(v.id, option)
  if (!res.ok) toast(res.message)
  else toast(option === 'agree' ? '已投「去吃」' : '已投「不去」')
}

function simulate(v) {
  const n = simulateVotes(v.id, 2)
  toast(n ? `模拟 ${n} 位同学投了票` : '这个投票已经结束')
}
</script>

<template>
  <div class="page vote">
    <section class="intro">
      <h1>吃不吃？让大家投</h1>
      <p class="intro-sub">
        设置目标人数，<b>同意票过半</b>就判定「去吃」。犹豫不决的时候，把决定权交出去。
      </p>
    </section>

    <section class="card create">
      <button v-if="!openForm" class="create-toggle" @click="openForm = true">＋ 发起一个投票</button>

      <template v-else>
        <div class="create-head">
          <h2>发起投票</h2>
          <button class="close" @click="openForm = false">取消</button>
        </div>

        <div class="create-body">
          <UField v-model="title" placeholder="投票标题，例如：今晚去吃鸡公煲？" />
          <UField v-model="target" placeholder="想吃什么（可留空）" />

          <div class="count-row">
            <span class="count-label">目标参与人数</span>
            <div class="stepper">
              <button @click="targetCount = Math.max(2, targetCount - 1)">−</button>
              <span>{{ targetCount }}</span>
              <button @click="targetCount = Math.min(99, targetCount + 1)">＋</button>
            </div>
            <span class="count-tip">过半需 {{ votesNeeded(targetCount) }} 票</span>
          </div>
        </div>

        <UButton type="primary" block @click="submit">发布投票</UButton>
      </template>
    </section>

    <div v-if="!state.votes.length" class="card empty">
      <span class="emoji">🗳️</span>
      还没有投票，发起第一个吧
    </div>

    <section class="list">
      <article v-for="v in state.votes" :key="v.id" class="card vote-card">
        <header class="vote-head">
          <h3>{{ v.title }}</h3>
          <span class="badge" :class="v.status">{{ voteStatusText(v) }}</span>
        </header>

        <p v-if="v.target" class="vote-target">🎯 {{ v.target }}</p>

        <UProgress :percentage="pct(v)" />

        <div class="vote-nums">
          <span class="agree">同意 {{ v.agree }}</span>
          <span class="disagree">反对 {{ v.disagree }}</span>
          <span class="need">
            {{ v.status === 'ongoing' ? `还需 ${remain(v)} 票通过` : `目标 ${v.targetCount} 人` }}
          </span>
        </div>

        <div class="vote-foot">
          <span class="muted">{{ fmtTime(v.createdAt) }} 发起</span>
          <div class="vote-actions">
            <UButton size="small" :disabled="v.status !== 'ongoing'" @click="vote(v, 'agree')">去吃</UButton>
            <UButton size="small" plain :disabled="v.status !== 'ongoing'" @click="vote(v, 'disagree')">不去</UButton>
            <UButton size="small" text :disabled="v.status !== 'ongoing'" @click="simulate(v)">模拟同学</UButton>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.intro {
  padding: 6px 0 20px;
}

.intro h1 {
  font-size: 30px;
  letter-spacing: -0.01em;
}

.intro-sub {
  margin-top: 8px;
  font-size: 14px;
  color: var(--muted);
}

.create {
  margin-bottom: 22px;
}

.create-toggle {
  width: 100%;
  padding: 14px;
  border: 1px dashed #ffc6ad;
  border-radius: 12px;
  background: #fff8f4;
  color: var(--brand);
  font-size: 14px;
  font-weight: 600;
}

.create-toggle:hover {
  border-color: var(--brand);
}

.create-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.create-head h2 {
  font-size: 16px;
}

.close {
  border: none;
  background: none;
  color: var(--muted);
  font-size: 13px;
}

.create-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.count-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  flex-wrap: wrap;
}

.count-label {
  font-size: 13px;
  color: #4a5160;
}

.count-tip {
  font-size: 12px;
  color: var(--muted);
}

.stepper {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.stepper button {
  width: 32px;
  height: 32px;
  border: none;
  background: #f7f8fa;
  color: #4a5160;
  font-size: 16px;
  line-height: 1;
}

.stepper button:hover {
  color: var(--brand);
}

.stepper span {
  min-width: 44px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.vote-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.vote-head h3 {
  font-size: 16px;
  line-height: 1.4;
}

.badge {
  flex-shrink: 0;
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  background: #f3f4f7;
  color: #6b7280;
  white-space: nowrap;
}

.badge.ongoing {
  background: #fff1ea;
  color: var(--brand);
}
.badge.passed {
  background: #e8f8ee;
  color: #1a9c56;
}
.badge.rejected {
  background: #fdeceb;
  color: #d64541;
}

.vote-target {
  margin: 8px 0 12px;
  font-size: 13px;
  color: #4a5160;
}

.vote-nums {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 10px 0 14px;
  font-size: 12px;
  color: var(--muted);
}

.vote-nums .agree {
  color: #1a9c56;
  font-weight: 600;
}

.vote-nums .disagree {
  color: #d64541;
  font-weight: 600;
}

.vote-nums .need {
  margin-left: auto;
}

.vote-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
  flex-wrap: wrap;
}

.vote-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 820px) {
  .intro h1 {
    font-size: 24px;
  }
  .vote-foot {
    align-items: stretch;
  }
  .vote-actions {
    justify-content: flex-end;
  }
}
</style>
