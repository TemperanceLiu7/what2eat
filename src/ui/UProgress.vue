<script setup>
import { useIsMobile } from '@/composables/useIsMobile'

defineProps({ percentage: { type: Number, default: 0 } })

const isMobile = useIsMobile()
const color = '#b03a2e'
</script>

<template>
  <van-progress
    v-if="isMobile"
    :percentage="percentage"
    :show-pivot="false"
    :stroke-width="8"
    :color="color"
    track-color="#f0f1f4"
  />
  <el-progress
    v-else
    :percentage="percentage"
    :show-text="false"
    :stroke-width="8"
    :color="color"
  />
</template>
