<script setup>
import { isLoggedIn, isVerified } from '@/stores/app'
</script>

<template>
  <div class="shell mobile">
    <header class="m-header">
      <router-link to="/" class="m-brand">
        <span class="m-mark">吃</span>
        <span>今天吃什么</span>
      </router-link>
      <router-link :to="isLoggedIn ? '/me' : '/login'" class="m-user">
        <van-tag v-if="isVerified" type="success" round>已认证</van-tag>
        <van-tag v-else-if="isLoggedIn" round color="var(--brand-soft)" text-color="var(--brand)">未核验</van-tag>
        <van-tag v-else round color="var(--surface-soft)" text-color="var(--ink-soft)">登录</van-tag>
      </router-link>
    </header>

    <main class="m-main">
      <router-view />
    </main>

    <van-tabbar
      route
      :border="false"
      active-color="var(--brand-strong)"
      inactive-color="var(--muted)"
      safe-area-inset-bottom
      class="m-tabbar"
    >
      <van-tabbar-item replace to="/personal" icon="home-o">个人</van-tabbar-item>
      <van-tabbar-item replace to="/community" icon="friends-o">社区</van-tabbar-item>
      <van-tabbar-item replace to="/me" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
}

.m-header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 48px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: color-mix(in srgb, var(--bg) 90%, transparent);
  backdrop-filter: saturate(160%) blur(12px);
  border-bottom: 1px dashed var(--brand-line-soft);
  padding-top: env(safe-area-inset-top);
}

.m-brand {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 600;
}

.m-mark {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand);
  color: #fff;
  border-radius: 2px;
  font-size: 12px;
  line-height: 1;
}

.m-user {
  display: flex;
  align-items: center;
}

.m-main {
  padding-bottom: 64px;
}

.m-tabbar {
  border-top: 1px solid var(--line);
}

.m-tabbar :deep(.van-tabbar-item__text) {
  font-size: 11px;
}
</style>
