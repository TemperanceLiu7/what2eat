<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { addCheckin, recognizeImage } from '@/api'
import { isLoggedIn, isVerified, loadPreferences, ui } from '@/stores/app'
import { readImage } from '@/utils/image'
import { toast } from '@/composables/useToast'
import UField from '@/ui/UField.vue'
import UButton from '@/ui/UButton.vue'

const router = useRouter()

const image = ref('')
const content = ref('')
const dishName = ref('')
const visibility = ref('private')
const busy = ref(false)

const candidates = ref([])
const recognizeNote = ref('')
const recognizing = ref(false)
const recognized = ref(false)

const canSubmit = computed(
  () => isVerified.value && (dishName.value.trim() || content.value.trim()) && !busy.value,
)

onMounted(() => {
  if (!isLoggedIn.value) {
    toast('先登录才能记录自己吃了什么')
  }
})

async function onFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return

  busy.value = true
  try {
    image.value = await readImage(file)
  } catch {
    toast('图片处理失败，换一张试试')
    busy.value = false
    return
  }
  busy.value = false

  // 图片就绪后自动识别
  await runRecognize()
}

async function runRecognize() {
  if (!image.value) return
  recognizing.value = true
  recognized.value = false
  candidates.value = []
  recognizeNote.value = ''
  try {
    const res = await recognizeImage(image.value)
    recognized.value = true
    candidates.value = res.dishes || []
    recognizeNote.value = res.note || ''
    if (candidates.value.length) {
      dishName.value = candidates.value[0].name
      toast(`识别到：${candidates.value[0].name}，不对的话可以改`)
    } else {
      toast(res.ready === false ? '识别服务未启用，手动填一下菜名' : '没认出这是什么，手动填一下')
    }
  } catch (err) {
    recognized.value = true
    recognizeNote.value = err?.message || '识别失败'
    toast('识别失败，手动填一下吧')
  } finally {
    recognizing.value = false
  }
}

function pick(c) {
  dishName.value = c.name
}

async function submit() {
  if (!isLoggedIn.value) {
    router.push({ path: '/login', query: { redirect: '/eat' } })
    return
  }
  busy.value = true
  try {
    const res = await addCheckin({
      content: content.value.trim() || dishName.value.trim(),
      image: image.value,
      dishName: dishName.value.trim(),
      visibility: visibility.value,
    })
    if (!res.ok) {
      toast(res.message)
      if (res.code === 'UNVERIFIED') router.push('/login')
      return
    }
    toast(visibility.value === 'private' ? '已记下（仅自己可见）' : '已发布到社区')
    image.value = ''
    content.value = ''
    dishName.value = ''
    candidates.value = []
    recognized.value = false
    await loadPreferences()
    router.push('/personal')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page eat">
    <section class="head">
      <p class="kicker">个人板块</p>
      <h1>今天吃了啥</h1>
      <p class="sub">拍照或选图，自动识别菜品，记录会计入你的口味偏好。</p>
    </section>

    <section class="card panel">
      <!-- 图片区 -->
      <label class="picker" :class="{ filled: !!image }">
        <input type="file" accept="image/*" capture="environment" hidden @change="onFile" />
        <img v-if="image" :src="image" alt="吃的照片" />
        <span v-else class="picker-inner">
          <svg class="icon" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2.1l1.3-2h6.2l1.3 2h2.1A1.5 1.5 0 0 1 20 8.5V18a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18z" />
            <circle cx="12" cy="12.8" r="3.2" />
          </svg>
          <span class="text">拍照 / 选图</span>
          <span class="hint">支持直接调用后置摄像头</span>
        </span>
      </label>

      <!-- 识别结果 -->
      <div v-if="recognizing" class="recognize loading">正在识别图片里的菜…</div>

      <div v-else-if="recognized" class="recognize">
        <div v-if="candidates.length" class="candidates">
          <span class="label">识别结果（点一下换）</span>
          <div class="chips">
            <button
              v-for="c in candidates"
              :key="c.name"
              class="chip"
              :class="{ active: dishName === c.name }"
              @click="pick(c)"
            >
              {{ c.name }}<em>{{ Math.round(c.confidence * 100) }}%</em>
            </button>
          </div>
        </div>
        <p v-else class="note">{{ recognizeNote || '没认出是什么，手动填一下吧' }}</p>
        <button class="retry" @click="runRecognize">重新识别</button>
      </div>

      <UField v-model="dishName" placeholder="菜名（识别不准可以手动改）" />
      <UField v-model="content" textarea :rows="2" placeholder="好吃吗？给未来的自己留一句" />

      <!-- 可见范围 -->
      <div class="scope">
        <span class="label">这条记录</span>
        <div class="chips">
          <button class="chip" :class="{ active: visibility === 'private' }" @click="visibility = 'private'">
            仅自己可见
          </button>
          <button class="chip" :class="{ active: visibility === 'public' }" @click="visibility = 'public'">
            公开到社区
          </button>
        </div>
      </div>
      <p class="scope-tip">
        私密记录不会出现在社区、也不会被别人举报，但<strong>一样计入你的口味偏好</strong>和随机推荐的去重。
      </p>

      <div class="foot">
        <UButton
          type="primary"
          block
          :disabled="!canSubmit"
          :loading="busy"
          @click="submit"
        >
          {{ visibility === 'private' ? '保存到我的记录' : '发布到社区' }}
        </UButton>
      </div>
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
  color: var(--muted);
  font-size: 14px;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.picker {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 180px;
  border-radius: var(--radius-md);
  border: 1px dashed var(--brand-line);
  background: var(--surface-warm);
  overflow: hidden;
  cursor: pointer;
}

.picker.filled {
  border-style: solid;
  border-color: transparent;
}

.picker img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.picker-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--brand-2-deep);
}

.icon {
  font-size: 28px;
}

.text {
  font-size: 14px;
  font-weight: 600;
}

.hint {
  font-size: 12px;
  opacity: 0.75;
}

.recognize {
  background: var(--surface-soft);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  font-size: 13px;
  color: var(--ink-soft);
}

.recognize.loading {
  color: var(--muted);
}

.label {
  font-size: 12px;
  color: var(--muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.chip em {
  font-style: normal;
  font-size: 11px;
  opacity: 0.6;
  margin-left: 4px;
}

.note {
  font-size: 13px;
  color: var(--muted);
}

.retry {
  margin-top: 6px;
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: var(--brand);
}

.scope {
  margin-top: 4px;
}

.scope-tip {
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
}

.scope-tip strong {
  color: var(--brand-2-deep);
}

@media (max-width: 820px) {
  h1 {
    font-size: 22px;
  }
  .picker {
    height: 150px;
  }
}
</style>
