<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usingMock } from '@/api'
import { bindStudent, isVerified, login, register, ui } from '@/stores/app'
import { toast } from '@/composables/useToast'
import UField from '@/ui/UField.vue'
import UButton from '@/ui/UButton.vue'

const route = useRoute()
const router = useRouter()

// login | register | verify
const step = ref('login')
const tab = ref('login')
const busy = ref(false)

const form = ref({
  username: '',
  password: '',
  name: '',
  college: '',
  studentId: '',
})

const redirect = computed(() => route.query.redirect || '/')

const title = computed(() => {
  if (step.value === 'verify') return '完成学号核验'
  return tab.value === 'login' ? '登录' : '注册'
})

function switchTab(next) {
  tab.value = next
  step.value = next
  busy.value = false
}

async function submit() {
  if (busy.value) return
  busy.value = true
  try {
    if (step.value === 'login') {
      const res = await login({ username: form.value.username.trim(), password: form.value.password })
      if (!res.ok) return toast(res.message)
      toast(res.message || '登录成功')
      return afterAuth()
    }

    if (step.value === 'register') {
      const res = await register({
        username: form.value.username.trim(),
        password: form.value.password,
        name: form.value.name.trim(),
        college: form.value.college.trim(),
        student_id: form.value.studentId.trim(),
      })
      if (!res.ok) return toast(res.message)
      toast('注册成功，接着完成学号核验')
      step.value = 'verify'
      return
    }

    // 核验
    const res = await bindStudent({
      studentId: form.value.studentId.trim(),
      name: form.value.name.trim(),
      college: form.value.college.trim(),
    })
    if (!res.ok) return toast(res.message)
    toast(res.message || '核验通过')
    router.replace(redirect.value)
  } finally {
    busy.value = false
  }
}

function afterAuth() {
  if (isVerified.value) router.replace(redirect.value)
  else step.value = 'verify'
}

function fillDemo() {
  form.value.username = 'admin'
  form.value.password = 'admin123456'
}

function fillMockDemo() {
  form.value.username = '20230001'
  form.value.password = '123456'
}
</script>

<template>
  <div class="page login">
    <section class="card panel">
      <p class="kicker">{{ usingMock ? '演示模式' : '校园账号' }}</p>
      <h1>{{ title }}</h1>

      <!-- 登录 / 注册 切换 -->
      <div v-if="step !== 'verify'" class="tabs">
        <button class="chip" :class="{ active: tab === 'login' }" @click="switchTab('login')">登录</button>
        <button class="chip" :class="{ active: tab === 'register' }" @click="switchTab('register')">注册</button>
      </div>

      <p v-if="step === 'verify'" class="hint">
        为了挡住商家打广告，发布内容前必须核验学号、姓名、学院三项与学籍数据一致。
        你现在登录的是
        <b>{{ ui.user?.username || '—' }}</b>
        ，核验通过后才能发打卡、发起投票。
      </p>

      <div class="fields">
        <template v-if="step === 'login'">
          <UField v-model="form.username" placeholder="账号" />
          <UField v-model="form.password" placeholder="密码" />
        </template>

        <template v-else-if="step === 'register'">
          <UField v-model="form.username" placeholder="账号（至少 3 位）" />
          <UField v-model="form.password" placeholder="密码（至少 6 位）" />
          <UField v-model="form.name" placeholder="姓名" />
          <UField v-model="form.college" placeholder="学院" />
        </template>

        <template v-else>
          <UField v-model="form.studentId" placeholder="学号，如 20230001" />
          <UField v-model="form.name" placeholder="姓名" />
          <UField v-model="form.college" placeholder="学院，如 计算机学院" />
        </template>
      </div>

      <UButton type="primary" block :loading="busy" @click="submit">
        {{ step === 'login' ? '登录' : step === 'register' ? '注册' : '提交核验' }}
      </UButton>

      <div class="foot">
        <button v-if="step === 'register'" class="link" @click="switchTab('login')">已有账号？去登录</button>
        <button v-else-if="step === 'login'" class="link" @click="switchTab('register')">没有账号？去注册</button>

        <button v-if="usingMock" class="link" @click="fillMockDemo">填入演示账号（20230001 / 123456）</button>
        <button v-else class="link" @click="fillDemo">填入管理员账号（admin）</button>
      </div>

      <p v-if="usingMock" class="hint small">
        当前是演示模式（数据存在浏览器里）。切到真后端后，这里的账号就是数据库里的真实用户。
      </p>
    </section>
  </div>
</template>

<style scoped>
.login {
  display: flex;
  justify-content: center;
  padding-top: 6vh;
}

.panel {
  width: min(420px, 100%);
  padding: 28px;
}

.kicker {
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--brand);
  font-weight: 600;
  margin-bottom: 6px;
}

h1 {
  font-size: 24px;
  margin-bottom: 16px;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.fields {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.hint {
  font-size: 13px;
  line-height: 1.7;
  color: var(--muted);
  margin-bottom: 16px;
}

.hint.small {
  margin: 14px 0 0;
  font-size: 12px;
}

.foot {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.link {
  border: none;
  background: none;
  padding: 0;
  color: var(--brand);
  font-size: 13px;
}

.link:hover {
  text-decoration: underline;
}

@media (max-width: 820px) {
  .login {
    padding-top: 12px;
  }
  .panel {
    padding: 20px;
  }
}
</style>
