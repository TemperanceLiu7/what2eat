<script setup>
import { computed, ref, watch } from 'vue'
import { report, usingMock } from '@/api'
import { isLoggedIn, isVerified } from '@/stores/app'
import { toast } from '@/composables/useToast'
import UButton from '@/ui/UButton.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  // { reportedId, targetType, targetId, title }
  target: { type: Object, default: null },
})
const emit = defineEmits(['close', 'submitted'])

const REASONS = ['广告推销', '违规内容', '恶意刷屏', '其他']

const reason = ref(REASONS[0])
const detail = ref('')
const busy = ref(false)

watch(
  () => props.open,
  (open) => {
    if (open) {
      reason.value = REASONS[0]
      detail.value = ''
      busy.value = false
    }
  },
)

/** 拼成后端认的 reason 字符串（最多 200 字） */
const finalReason = computed(() => {
  const text = detail.value.trim()
  if (reason.value === '其他') return text
  return text ? `${reason.value}：${text}` : reason.value
})

const canSubmit = computed(() => Boolean(finalReason.value) && !busy.value)

async function submit() {
  if (!isLoggedIn.value) {
    toast('请先登录再举报')
    emit('close')
    return
  }
  if (!isVerified.value) {
    toast('举报前需要先完成学号核验')
    emit('close')
    return
  }
  // mock 的打卡记录没有作者 id，演示模式不强求；真接口必须有
  if (!usingMock && !props.target?.reportedId) {
    toast('这条内容没有可举报的作者')
    return
  }

  busy.value = true
  try {
    const res = await report({
      reportedId: props.target?.reportedId ?? 0,
      targetType: props.target?.targetType || 'checkin',
      targetId: props.target?.targetId,
      reason: finalReason.value.slice(0, 200),
    })
    toast(res.message)
    if (res.ok) {
      emit('submitted', res)
      emit('close')
    }
  } catch (err) {
    toast(err?.message || '举报失败，稍后再试')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Transition name="fade">
    <div v-if="open" class="overlay" @click.self="emit('close')">
      <div class="dialog" role="dialog" aria-modal="true">
        <div class="head">
          <h3>举报这条内容</h3>
          <button class="x" aria-label="关闭" @click="emit('close')">×</button>
        </div>

        <p v-if="target?.title" class="quote">{{ target.title }}</p>

        <p class="tip">管理员会核实举报；累计多次违规会被禁言。恶意举报同样会被处理。</p>

        <div class="reasons">
          <button
            v-for="r in REASONS"
            :key="r"
            class="chip"
            :class="{ active: reason === r }"
            @click="reason = r"
          >
            {{ r }}
          </button>
        </div>

        <textarea
          v-model="detail"
          class="detail"
          rows="3"
          maxlength="120"
          :placeholder="reason === '其他' ? '说说具体哪里违规（必填）' : '补充说明（选填）'"
        />

        <div class="foot">
          <span class="count">{{ finalReason.length }}/200</span>
          <div class="actions">
            <UButton plain @click="emit('close')">取消</UButton>
            <UButton type="primary" :disabled="!canSubmit" :loading="busy" @click="submit">
              提交举报
            </UButton>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(20, 22, 26, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.dialog {
  width: min(460px, 100%);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.head h3 {
  font-size: 16px;
}

.x {
  border: none;
  background: none;
  font-size: 22px;
  line-height: 1;
  color: var(--muted);
  padding: 0 4px;
}

.x:hover {
  color: var(--ink);
}

.quote {
  font-size: 13px;
  color: var(--ink-soft);
  background: var(--surface-soft);
  border-left: 3px solid var(--brand-line);
  border-radius: var(--radius-md);
  padding: 8px 10px;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tip {
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
  margin-bottom: 12px;
}

.reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.detail {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  font: inherit;
  font-size: 13px;
  resize: none;
  outline: none;
}

.detail:focus {
  border-color: var(--brand-line);
}

.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
}

.count {
  font-size: 12px;
  color: var(--muted);
}

.actions {
  display: flex;
  gap: 8px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 820px) {
  .overlay {
    align-items: flex-end;
    padding: 0;
  }
  .dialog {
    width: 100%;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    padding: 18px 16px calc(18px + env(safe-area-inset-bottom));
  }
}
</style>
