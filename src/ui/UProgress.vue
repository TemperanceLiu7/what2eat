<script setup>
import { useIsMobile } from '@/composables/useIsMobile'

defineProps({ percentage: { type: Number, default: 0 } })

const isMobile = useIsMobile()
</script>

<template>
  <van-progress
    v-if="isMobile"
    :percentage="percentage"
    :show-pivot="false"
    :stroke-width="8"
    color="var(--brand)"
    track-color="var(--surface-soft)"
  />
  <el-progress
    v-else
    :percentage="percentage"
    :show-text="false"
    :stroke-width="8"
    color="var(--brand)"
  />
</template>
