<script setup>
import { computed } from 'vue'
import { useIsMobile } from '@/composables/useIsMobile'

const props = defineProps({
  type: { type: String, default: 'default' }, // primary | default
  size: { type: String, default: 'medium' }, // small | medium | large
  block: Boolean,
  plain: Boolean,
  text: Boolean,
  disabled: Boolean,
  loading: Boolean,
})
defineEmits(['click'])

const isMobile = useIsMobile()
const elType = computed(() => (props.type === 'primary' ? 'primary' : ''))
const elSize = computed(() =>
  props.size === 'small' ? 'small' : props.size === 'large' ? 'large' : 'default',
)
</script>

<template>
  <van-button
    v-if="isMobile"
    :type="type === 'primary' ? 'primary' : 'default'"
    :size="size"
    :block="block"
    :plain="plain"
    :disabled="disabled"
    :loading="loading"
    :class="['u-btn', { 'u-btn--text': text }]"
    @click="$emit('click', $event)"
  >
    <slot />
  </van-button>
  <el-button
    v-else
    :type="elType"
    :size="elSize"
    :plain="plain"
    :text="text"
    :disabled="disabled"
    :loading="loading"
    :class="['u-btn', { 'u-btn--block': block }]"
    @click="$emit('click', $event)"
  >
    <slot />
  </el-button>
</template>

<style scoped>
.u-btn--block {
  width: 100%;
}
.u-btn--text {
  padding: 0 4px;
}

/*
 * 按钮统一成"印刷品"质感：方角、无投影、字重不过粗、按下只变色不缩放。
 * 两个组件库各覆盖一次，保证同一按钮在 PC / 手机上一模一样。
 */
.u-btn {
  font-family: var(--font-sans);
  font-weight: 500;
  letter-spacing: 0.02em;
  border-radius: var(--radius-sm);
  box-shadow: none;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    border-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out);
}

.u-btn:active {
  transform: none;
}
</style>
