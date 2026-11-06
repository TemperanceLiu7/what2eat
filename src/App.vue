<script setup>
import { useIsMobile } from '@/composables/useIsMobile'
import { defineAsyncComponent } from 'vue'
import ToastHost from '@/components/ToastHost.vue'

// 两套外壳各自懒加载：PC 用户不会下载 Vant 的 tabbar，手机用户不会下载 Element Plus 的菜单
const PcShell = defineAsyncComponent(() => import('@/layouts/PcShell.vue'))
const MobileShell = defineAsyncComponent(() => import('@/layouts/MobileShell.vue'))

const isMobile = useIsMobile()
</script>

<template>
  <component :is="isMobile ? MobileShell : PcShell" />
  <ToastHost />
</template>
