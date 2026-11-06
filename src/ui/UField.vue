<script setup>
import { useIsMobile } from '@/composables/useIsMobile'

const model = defineModel({ type: String, default: '' })
defineProps({
  placeholder: { type: String, default: '' },
  textarea: Boolean,
  rows: { type: Number, default: 3 },
  maxlength: { type: Number, default: 200 },
})

const isMobile = useIsMobile()
</script>

<template>
  <van-field
    v-if="isMobile"
    v-model="model"
    :type="textarea ? 'textarea' : 'text'"
    :rows="rows"
    :placeholder="placeholder"
    :maxlength="maxlength"
    class="u-field u-field--mobile"
  />
  <el-input
    v-else
    v-model="model"
    :type="textarea ? 'textarea' : 'text'"
    :rows="rows"
    :placeholder="placeholder"
    :maxlength="maxlength"
    resize="none"
    class="u-field"
  />
</template>

<style scoped>
/* Vant 的 field 默认没有边框，单独用时看起来像悬空的文字，这里补一个浅底盒子 */
.u-field--mobile {
  background: #f7f8fa;
  border: 1px solid var(--line);
  border-radius: 10px;
  margin-bottom: 10px;
  padding: 2px 4px;
}
</style>
