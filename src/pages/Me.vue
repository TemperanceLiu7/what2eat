<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toggleFavorite, usingMock } from '@/api'
import {
  bindStudent,
  isLoggedIn,
  isMuted,
  isVerified,
  loadCheckins,
  loadFavorites,
  loadVotes,
  logout,
  mutedUntilText,
  ui,
} from '@/stores/app'
import { DEMO_STUDENT } from '@/data/db'
import { toast } from '@/composables/useToast'
import UField from '@/ui/UField.vue'
import UButton from '@/ui/UButton.vue'
import ThemeSwitcher from '@/ui/ThemeSwitcher.vue'

const router = useRouter()

const sid = ref('')
const name = ref('')
const college = ref('')

const stats = computed(() => [
  { label: '打卡', value: ui.checkins.length },
  { label: '收藏', value: Object.keys(ui.favorites).length },
  { label: '点赞', value: Object.keys(ui.likes).length },
  { label: '投票', value: ui.votes.length },
])

const favs = computed(() => ui.favoriteList || [])

const recent = computed(() => ui.eaten.slice(0, 5))

const passing = computed(() => ui.votes.filter((v) => v.status === 'passed').length)

async function refreshAll() {
  if (!isLoggedIn.value) return
  await Promise.allSettled([loadCheckins(), loadVotes(), loadFavorites()])
}

onMounted(refreshAll)

async function doVerify() {
  if (!isLoggedIn.value) {
    toast('请先登录，再核验学号')
    router.push({ path: '/login', query: { redirect: '/me' } })
    return
  }
  const res = await bindStudent({
    studentId: sid.value.trim(),
    name: name.value.trim(),
    college: college.value.trim(),
  })
  toast(res.message)
  if (res.ok) await refreshAll()
}

function fillDemo() {
  sid.value = DEMO_STUDENT.studentId
  name.value = DEMO_STUDENT.name
  college.value = DEMO_STUDENT.college
}

async function unfav(id) {
  try {
    await toggleFavorite('dish', id)
    toast('已取消收藏')
    await loadFavorites()
  } catch (err) {
    toast(err?.message || '操作失败')
  }
}

async function doLogout() {
  await logout()
  toast('已退出登录')
  router.replace('/login')
}

function resetAll() {
  localStorage.removeItem('what2eat:v1')
  localStorage.removeItem('what2eat:user')
  localStorage.removeItem('what2eat:eaten')
  toast('演示数据已清空，正在刷新')
  setTimeout(() => location.reload(), 500)
}
</script>

<template>
  <div class="page me">
    <h1 class="me-title">我的</h1>

    <!-- 界面主题 -->
    <section class="card theme-card">
      <div class="section-head">
        <h2>界面主题</h2>
        <span class="sub">配色与贴纸随心换</span>
      </div>
      <ThemeSwitcher />
    </section>

    <!-- 身份验证 -->
    <section v-if="!isLoggedIn" class="card verify">
      <div class="section-head">
        <h2>还没有登录</h2>
        <span class="sub">登录后才能核验</span>
      </div>
      <p class="muted">随机推荐不需要登录，但发打卡、发起投票、收藏都需要一个校园账号，且必须完成学号核验。</p>
      <UButton type="primary" block @click="router.push({ path: '/login', query: { redirect: '/me' } })">
        去登录 / 注册
      </UButton>
    </section>

    <section v-else-if="!isVerified" class="card verify">
      <div class="section-head">
        <h2>学生身份核验</h2>
        <span class="sub">发布内容的前置条件</span>
      </div>
      <p class="muted">
        学号、姓名、学院三项与学校学籍数据一致才能绑定。商家拿不到在读学生的学号，所以进不来——
        这是这个平台和普通美食应用最大的区别。
      </p>

      <div class="verify-form">
        <UField v-model="sid" placeholder="学号，如 20230001" />
        <UField v-model="name" placeholder="姓名" />
        <UField v-model="college" placeholder="学院，如 计算机学院" />
        <UButton type="primary" block @click="doVerify">提交核验</UButton>
      </div>

      <button class="demo-fill" @click="fillDemo">
        没有学籍数据？点这里填入演示账号（{{ DEMO_STUDENT.studentId }} / {{ DEMO_STUDENT.name }} /
        {{ DEMO_STUDENT.college }}）
      </button>
    </section>

    <section v-else class="card verified-card">
      <div class="v-row">
        <span class="v-badge">已认证学生</span>
        <span class="v-id">{{ ui.user?.studentId }}</span>
      </div>
      <p class="v-name">{{ ui.user?.name }} · {{ ui.user?.college }}</p>
      <p v-if="isMuted" class="muted-warn">
        注意：账号已被{{ ui.user?.banned ? '封禁' : '禁言' }}<span v-if="mutedUntilText">，解禁时间 {{ mutedUntilText }}</span>
        ，期间无法发布内容。
      </p>
      <p v-else-if="ui.user?.reportCount" class="muted-warn soft">
        累计被举报 {{ ui.user.reportCount }} 次，请注意发布内容。
      </p>
      <p class="muted">一个学号只能绑定一个账号，发布打卡与投票时后端会再次校验绑定状态。</p>
    </section>

    <!-- 数据统计 -->
    <section class="stats">
      <div v-for="s in stats" :key="s.label" class="stat">
        <span class="stat-value">{{ s.value }}</span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
    </section>

    <p v-if="ui.votes.length" class="muted pass-tip">
      已发起 {{ ui.votes.length }} 个投票，其中 {{ passing }} 个达到「过半同意」。
    </p>

    <!-- 收藏 -->
    <section class="block">
      <div class="section-head">
        <h2>我的收藏</h2>
        <span class="sub">{{ favs.length }} 个</span>
      </div>

      <div v-if="!favs.length" class="card empty">
        在「随机推荐」里收藏喜欢的菜，会出现在这里
      </div>

      <div v-else class="fav-list">
        <div v-for="d in favs" :key="d.id" class="card fav-item">
          <span class="fav-emoji">{{ d.emoji }}</span>
          <div class="fav-body">
            <p class="fav-name">{{ d.name }}</p>
            <p class="muted">{{ d.shop?.name }} · ¥{{ d.price }}</p>
          </div>
          <button class="fav-remove" @click="unfav(d.id)">取消</button>
        </div>
      </div>
    </section>

    <!-- 最近吃过 -->
    <section v-if="recent.length" class="block">
      <div class="section-head">
        <h2>最近摇到</h2>
        <span class="sub">随机推荐会自动避开这些</span>
      </div>
      <ul class="recent-list card">
        <li v-for="d in recent" :key="d.id">
          <span class="r-emoji">{{ d.emoji }}</span>
          <span class="r-name">{{ d.name }}</span>
          <span class="muted">{{ d.shop?.name }}</span>
        </li>
      </ul>
    </section>

    <section class="block">
      <button v-if="isLoggedIn" class="reset" @click="doLogout">退出登录</button>
      <button v-if="usingMock" class="reset" @click="resetAll">清空演示数据</button>
      <p class="muted reset-tip">
        {{
          usingMock
            ? '当前是演示模式：数据只存在这台设备的浏览器里，换个设备就是全新的。'
            : '当前已连接后端：数据保存在服务器数据库，换设备登录同一账号即可看到。'
        }}
      </p>
    </section>
  </div>
</template>

<style scoped>
.me-title {
  font-size: 28px;
  margin-bottom: 18px;
}

.theme-card {
  margin-bottom: 18px;
}

.theme-card :deep(.theme-switcher) {
  margin-top: 10px;
}

.verify {
  margin-bottom: 18px;
}

.verify p {
  margin-bottom: 14px;
}

.verify-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 420px;
}

.demo-fill {
  margin-top: 14px;
  border: none;
  background: none;
  padding: 0;
  color: var(--brand);
  font-size: 12px;
  text-align: left;
  line-height: 1.6;
}

.verified-card {
  margin-bottom: 18px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 2px solid var(--brand-2);
}

.v-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.v-badge {
  font-size: 15px;
  font-weight: 700;
  color: var(--brand-2-deep);
}

.v-id {
  font-size: 12px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.v-name {
  font-size: 14px;
  margin-bottom: 8px;
}

.muted-warn {
  font-size: 13px;
  line-height: 1.6;
  color: var(--brand);
  background: var(--brand-soft);
  border-radius: var(--radius-md);
  padding: 8px 10px;
  margin-bottom: 10px;
}

.muted-warn.soft {
  color: var(--brand-2-deep);
  background: var(--surface-soft);
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}

.stat {
  background: #fff;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-emoji {
  font-size: 16px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 12px;
  color: var(--muted);
}

.pass-tip {
  margin: 10px 0 0;
}

.block {
  margin-top: 26px;
}

.fav-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.fav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
}

.fav-emoji {
  font-size: 24px;
}

.fav-body {
  flex: 1;
  min-width: 0;
}

.fav-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.fav-remove {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: var(--radius-md);
  padding: 5px 10px;
  font-size: 12px;
  color: var(--muted);
  flex-shrink: 0;
}

.fav-remove:hover {
  color: var(--brand);
  border-color: var(--brand-line);
}

.recent-list {
  list-style: none;
  padding: 6px 18px;
}

.recent-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 14px;
}

.recent-list li:last-child {
  border-bottom: none;
}

.r-emoji {
  font-size: 16px;
}

.r-name {
  flex: 1;
}

.reset {
  width: 100%;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  font-size: 13px;
}

.reset:hover {
  color: var(--brand);
  border-color: var(--brand-line);
}

.reset-tip {
  margin-top: 10px;
  text-align: center;
  font-size: 12px;
}

@media (max-width: 820px) {
  .me-title {
    font-size: 22px;
    margin-bottom: 14px;
  }
  .stats {
    gap: 8px;
  }
  .fav-list {
    grid-template-columns: 1fr;
  }
  .verify-form {
    max-width: none;
  }
}
</style>
