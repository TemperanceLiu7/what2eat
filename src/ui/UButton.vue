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
</style>
