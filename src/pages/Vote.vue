<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { castVote, createVote, requestReview, simulateVotes, usingMock } from '@/api'
import { isLoggedIn, isMuted, isVerified, loadVotes, mutedUntilText, ui } from '@/stores/app'
import { fmtTime, votesNeeded, voteStatusText } from '@/data/db'
import { toast } from '@/composables/useToast'
import UField from '@/ui/UField.vue'
import UButton from '@/ui/UButton.vue'
import UProgress from '@/ui/UProgress.vue'

const router = useRouter()

const title = ref('')
const target = ref('')
const targetCount = ref(6)
const openForm = ref(false)

const verified = computed(() => isVerified.value)
const pct = (v) => Math.min(100, Math.round(((v.agree || 0) / (v.targetCount || 1)) * 100))
const remain = (v) => Math.max(0, votesNeeded(v.targetCount) - v.agree)

onMounted(async () => {
  try {
    await loadVotes()
  } catch (err) {
    toast(err?.message || '投票列表加载失败')
  }
})

async function submit() {
  if (!isLoggedIn.value) {
    toast('请先登录')
    router.push({ path: '/login', query: { redirect: '/vote' } })
    return
  }
  const res = await createVote({ title: title.value, target: target.value, targetCount: targetCount.value })
  if (!res.ok) {
    toast(res.message)
    if (res.code === 'UNVERIFIED') router.push('/login')
    return
  }
  toast('投票已发起，拉同学来投')
  title.value = ''
  target.value = ''
  targetCount.value = 6
  openForm.value = false
  await loadVotes()
}

async function vote(v, option) {
  if (!isLoggedIn.value) {
    toast('请先登录')
    router.push({ path: '/login', query: { redirect: '/vote' } })
    return
  }
  if (option === 'agree' && !verified.value) {
    toast('参与投票需要先完成学号核验')
    return
  }
  const res = await castVote(v.id, option)
  if (!res.ok) toast(res.message)
  else toast(option === 'agree' ? '已投「去吃」' : '已投「不去」')
  await loadVotes()
}

async function simulate(v) {
  const res = await simulateVotes(v.id, 2)
  toast(res.message || (res.count ? `模拟 ${res.count} 位同学投了票` : '这个投票已经结束'))
  await loadVotes()
}

// 复审状态
const reviewing = ref(null)

/** 能申请复审的条件：已出结果 + 没被复审过 + 自己参与过或就是发起人 */
function canReview(v) {
  if (v.status === 'ongoing') return false
  if (v.isReview || v.reviewOf) return false
  if (v.reviewedBy) return false
  if (!isLoggedIn.value) return false
  if (usingMock) return true
  return Boolean(v.my_option) || v.creator?.id === ui.user?.id
}

async function review(v) {
  reviewing.value = v.id
  try {
    const res = await requestReview(v.id)
    toast(res.message)
    if (res.ok) await loadVotes()
  } finally {
    reviewing.value = null
  }
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

    <section v-if="isMuted" class="card muted-banner">
      <strong>你当前处于禁言状态</strong>
      <span v-if="mutedUntilText">，解禁时间：{{ mutedUntilText }}</span>
      <p>禁言期间不能发起投票，也不能参与投票。</p>
    </section>

    <section class="card create">
      <button v-if="!openForm" class="create-toggle" :disabled="isMuted" @click="openForm = true">
        ＋ 发起一个投票
      </button>

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

    <div v-if="!ui.votes.length" class="card empty">
      还没有投票，发起第一个吧
    </div>

    <section class="list">
      <article v-for="v in ui.votes" :key="v.id" class="card vote-card">
        <header class="vote-head">
          <h3>
            <span v-if="v.isReview || v.reviewOf" class="review-tag">复审</span>
            {{ v.title }}
          </h3>
          <span class="badge" :class="v.status">{{ voteStatusText(v) }}</span>
        </header>

        <p v-if="v.reviewOf" class="review-from">由投票 #{{ v.reviewOf }} 复审而来，参与人数扩大到 {{ v.targetCount }} 人</p>

        <p v-if="v.target" class="vote-target">{{ v.target }}</p>

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
            <UButton size="small" text v-if="usingMock" :disabled="v.status !== 'ongoing'" @click="simulate(v)">模拟同学</UButton>
            <UButton
              v-if="canReview(v)"
              size="small"
              text
              :loading="reviewing === v.id"
              @click="review(v)"
            >
              申请复审
            </UButton>
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
  border: 1px dashed var(--brand-line);
  border-radius: var(--radius-md);
  background: var(--surface-warm);
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
  color: var(--ink-soft);
}

.count-tip {
  font-size: 12px;
  color: var(--muted);
}

.stepper {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #fff;
}

.stepper button {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--surface-soft);
  color: var(--ink-soft);
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
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
  color: var(--muted);
  white-space: nowrap;
}

.badge.ongoing {
  background: var(--brand-soft);
  color: var(--brand);
}
.badge.passed {
  background: var(--surface-soft);
  color: var(--brand-2-deep);
}
.badge.rejected {
  background: var(--brand-soft);
  color: var(--brand);
}

.vote-target {
  margin: 8px 0 12px;
  font-size: 13px;
  color: var(--ink-soft);
}



.create-toggle:disabled {
  opacity: 0.55;
  cursor: not-allowed;
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
  color: var(--brand-2-deep);
  font-weight: 600;
}

.vote-nums .disagree {
  color: var(--brand);
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

/* 复审 */
.review-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  margin-right: 6px;
  border-radius: var(--radius-md);
  background: var(--surface-soft);
  color: var(--ink-soft);
  vertical-align: 2px;
}

.review-from {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--ink-soft);
  background: var(--surface-soft);
  border-radius: var(--radius-md);
  padding: 6px 10px;
}
</style>
