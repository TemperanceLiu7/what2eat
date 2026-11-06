<script setup>
import { computed, ref } from 'vue'
import {
  state,
  DEMO_STUDENT,
  verifyStudent,
  favoriteDishes,
  toggleFavorite,
  allDishViews,
  fmtTime,
} from '@/data/db'
import { toast } from '@/composables/useToast'
import UField from '@/ui/UField.vue'
import UButton from '@/ui/UButton.vue'

const sid = ref('')
const name = ref('')
const college = ref('')

const stats = computed(() => [
  { label: '打卡', value: state.checkins.length, emoji: '📸' },
  { label: '收藏', value: Object.keys(state.favorites).length, emoji: '⭐' },
  { label: '点赞', value: Object.keys(state.likes).length, emoji: '❤️' },
  { label: '投票', value: state.votes.length, emoji: '🗳️' },
])

const favs = computed(() => favoriteDishes())

const recent = computed(() =>
  state.eaten
    .slice(0, 5)
    .map((e) => allDishViews().find((d) => d.id === e.dishId))
    .filter(Boolean),
)

const passing = computed(() => state.votes.filter((v) => v.status === 'passed').length)

function doVerify() {
  const res = verifyStudent({ studentId: sid.value, name: name.value, college: college.value })
  toast(res.message)
}

function fillDemo() {
  sid.value = DEMO_STUDENT.studentId
  name.value = DEMO_STUDENT.name
  college.value = DEMO_STUDENT.college
}

function unfav(id) {
  toggleFavorite(id)
  toast('已取消收藏')
}

function resetAll() {
  localStorage.removeItem('what2eat:v1')
  toast('演示数据已清空，正在刷新')
  setTimeout(() => location.reload(), 500)
}
</script>

<template>
  <div class="page me">
    <h1 class="me-title">我的</h1>

    <!-- 身份验证 -->
    <section v-if="!state.user.verified" class="card verify">
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
        <span class="v-badge">✅ 已认证学生</span>
        <span class="v-id">{{ state.user.studentId }}</span>
      </div>
      <p class="v-name">{{ state.user.name }} · {{ state.user.college }}</p>
      <p class="muted">一个学号只能绑定一个账号，发布打卡与投票时后端会再次校验绑定状态。</p>
    </section>

    <!-- 数据统计 -->
    <section class="stats">
      <div v-for="s in stats" :key="s.label" class="stat">
        <span class="stat-emoji">{{ s.emoji }}</span>
        <span class="stat-value">{{ s.value }}</span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
    </section>

    <p v-if="state.votes.length" class="muted pass-tip">
      已发起 {{ state.votes.length }} 个投票，其中 {{ passing }} 个达到「过半同意」。
    </p>

    <!-- 收藏 -->
    <section class="block">
      <div class="section-head">
        <h2>我的收藏</h2>
        <span class="sub">{{ favs.length }} 个</span>
      </div>

      <div v-if="!favs.length" class="card empty">
        <span class="emoji">⭐</span>
        在「随机推荐」里收藏喜欢的菜，会出现在这里
      </div>

      <div v-else class="fav-list">
        <div v-for="d in favs" :key="d.id" class="card fav-item">
          <span class="fav-emoji">{{ d.emoji }}</span>
          <div class="fav-body">
            <p class="fav-name">{{ d.name }}</p>
            <p class="muted">{{ d.shop.name }} · ¥{{ d.price }}</p>
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
          <span class="muted">{{ d.shop.name }}</span>
        </li>
      </ul>
    </section>

    <section class="block">
      <button class="reset" @click="resetAll">清空演示数据</button>
      <p class="muted reset-tip">
        数据只存在这台设备的浏览器里（localStorage），换个设备就是全新的。正式版会把这一层换成 Django 接口。
      </p>
    </section>
  </div>
</template>

<style scoped>
.me-title {
  font-size: 28px;
  margin-bottom: 18px;
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
  background: linear-gradient(135deg, #f2fbf6, #ffffff);
  border: 1px solid #d6f0e2;
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
  color: #1a9c56;
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

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}

.stat {
  background: #fff;
  border-radius: 14px;
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
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--muted);
  flex-shrink: 0;
}

.fav-remove:hover {
  color: var(--brand);
  border-color: #ffc6ad;
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
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
  color: #6b7280;
  font-size: 13px;
}

.reset:hover {
  color: #d64541;
  border-color: #f6c9c7;
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
