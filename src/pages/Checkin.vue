<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { addCheckin, usingMock } from '@/api'
import { isLoggedIn, isMuted, isVerified, loadCheckins, mutedUntilText, ui } from '@/stores/app'
import { fmtTime } from '@/data/db'
import { readImage } from '@/utils/image'
import { toast } from '@/composables/useToast'
import UField from '@/ui/UField.vue'
import UButton from '@/ui/UButton.vue'
import ReportDialog from '@/components/ReportDialog.vue'

const router = useRouter()

const content = ref('')
const image = ref('')
const dishName = ref('')
const busy = ref(false)
const listLoading = ref(false)

const reportOpen = ref(false)
const reportTarget = ref(null)

function openReport(c) {
  if (!isLoggedIn.value) {
    toast('请先登录')
    router.push({ path: '/login', query: { redirect: '/checkin' } })
    return
  }
  reportTarget.value = {
    reportedId: c.userId,
    targetType: 'checkin',
    targetId: c.id,
    title: c.content,
  }
  reportOpen.value = true
}

function onReported(res) {
  if (res?.autoMuted) toast('该用户举报量已达上限，已被自动禁言')
}

const verified = computed(() => isVerified.value)
const canSubmit = computed(() => verified.value && content.value.trim().length > 0 && !busy.value)

// 从最近摇到的菜里挑一个做关联，比下拉框更快（纯本地 UI 状态）
const quick = computed(() => ui.eaten.slice(0, 4))

onMounted(async () => {
  listLoading.value = true
  try {
    await loadCheckins()
  } catch (err) {
    toast(err?.message || '打卡列表加载失败')
  } finally {
    listLoading.value = false
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
  } finally {
    busy.value = false
  }
}

async function submit() {
  if (!isLoggedIn.value) {
    toast('请先登录')
    router.push({ path: '/login', query: { redirect: '/checkin' } })
    return
  }

  busy.value = true
  try {
    const res = await addCheckin({ content: content.value, image: image.value, dishName: dishName.value })
    if (!res.ok) {
      toast(res.message)
      if (res.code === 'UNVERIFIED') router.push('/login')
      return
    }
    toast('打卡成功 🎉')
    content.value = ''
    image.value = ''
    dishName.value = ''
    await loadCheckins()
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page checkin">
    <section v-if="isMuted" class="card muted-banner">
      <strong>你当前处于禁言状态</strong>
      <span v-if="mutedUntilText">，解禁时间：{{ mutedUntilText }}</span>
      <p>禁言期间不能发布打卡、发起投票或参与投票。如有异议可以联系管理员复核。</p>
    </section>

    <section class="card compose">
      <div class="section-head">
        <h2>记录今天这一口</h2>
        <span class="sub">文字 + 图片</span>
      </div>

      <div class="upload-row">
        <label class="picker">
          <input type="file" accept="image/*" capture="environment" hidden @change="onFile" />
          <img v-if="image" :src="image" alt="打卡照片" />
          <span v-else class="picker-inner">
            <span class="picker-icon">📷</span>
            <span class="picker-text">拍照 / 选图</span>
          </span>
        </label>

        <div class="upload-side">
          <UField v-model="content" textarea :rows="4" placeholder="吃了什么？味道怎么样？" />
        </div>
      </div>

      <div v-if="quick.length" class="quick">
        <span class="quick-label">关联菜品</span>
        <button
          v-for="d in quick"
          :key="d.id"
          class="chip"
          :class="{ active: dishName === d.name }"
          @click="dishName = dishName === d.name ? '' : d.name"
        >
          {{ d.emoji }} {{ d.name }}
        </button>
      </div>

      <div class="compose-foot">
        <span class="muted">
          {{ verified ? `将以 ${ui.user.name}（${ui.user.studentId}）发布` : '发布前需要先完成学号核验' }}
        </span>
        <UButton type="primary" :disabled="!canSubmit" :loading="busy" @click="submit">发布打卡</UButton>
      </div>
    </section>

    <section class="timeline">
      <div class="section-head">
        <h2>打卡时间线</h2>
        <span class="sub">{{ ui.checkins.length }} 条</span>
      </div>

      <div v-if="!ui.checkins.length" class="card empty">
        <span class="emoji">🥢</span>
        还没有打卡记录，发第一条吧
      </div>

      <article v-for="c in ui.checkins" :key="c.id" class="card checkin-card">
        <img v-if="c.image" :src="c.image" class="c-img" alt="打卡图片" />
        <div class="c-body">
          <div class="c-head">
            <span class="who">{{ c.who }}</span>
            <span class="when">{{ fmtTime(c.at) }}</span>
          </div>
          <p class="c-text">{{ c.content }}</p>
          <div class="c-foot">
            <span v-if="c.dishName" class="dish-tag">🍽️ {{ c.dishName }}</span>
            <button
              v-if="usingMock || (c.userId && c.userId !== ui.user?.id)"
              class="report-link"
              @click="openReport(c)"
            >
              举报
            </button>
          </div>
        </div>
      </article>
    </section>

    <ReportDialog
      :open="reportOpen"
      :target="reportTarget"
      @close="reportOpen = false"
      @submitted="onReported"
    />
  </div>
</template>

<style scoped>
.compose {
  margin-bottom: 26px;
}

.upload-row {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.picker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 200px;
  height: 148px;
  border-radius: 14px;
  border: 1px dashed #ffc6ad;
  background: #fff8f4;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.18s ease;
}

.picker:hover {
  border-color: var(--brand);
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
  gap: 6px;
  color: #b0752f;
}

.picker-icon {
  font-size: 26px;
}

.picker-text {
  font-size: 13px;
}

.quick {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.quick-label {
  font-size: 12px;
  color: var(--muted);
}

.compose-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.checkin-card {
  display: flex;
  gap: 16px;
  padding: 16px;
}

.c-img {
  width: 132px;
  height: 132px;
  object-fit: cover;
  border-radius: 12px;
  flex-shrink: 0;
}

.c-body {
  flex: 1;
  min-width: 0;
}

.c-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.who {
  font-weight: 600;
  font-size: 14px;
}

.when {
  font-size: 12px;
  color: var(--muted);
}

.c-text {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.6;
  color: #3d434d;
}

.dish-tag {
  display: inline-block;
  margin-top: 10px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #fff1ea;
  color: var(--brand);
}

/* 卡片底部：菜品标签 + 举报入口 */
.c-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.c-foot .dish-tag {
  margin-top: 0;
}

.report-link {
  margin-left: auto;
  border: none;
  background: none;
  padding: 2px 0;
  font-size: 12px;
  color: var(--muted);
  opacity: 0.85;
}

.report-link:hover {
  color: #d64541;
  text-decoration: underline;
}

/* 禁言提示 */
.muted-banner {
  margin-bottom: 16px;
  border: 1px solid #f6c9c7;
  background: #fdf3f2;
  color: #8a3b38;
  font-size: 13px;
  line-height: 1.7;
}

.muted-banner strong {
  font-size: 14px;
}

.muted-banner p {
  margin-top: 6px;
  font-size: 12px;
  color: #a2605c;
}

@media (max-width: 820px) {
  .upload-row {
    grid-template-columns: 1fr;
  }
  .picker {
    width: 100%;
    height: 120px;
  }
  .compose-foot {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    text-align: center;
  }
  .checkin-card {
    padding: 12px;
    gap: 12px;
  }
  .c-img {
    width: 92px;
    height: 92px;
  }
}
</style>
