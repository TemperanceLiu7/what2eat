<script setup>
import { isLoggedIn, isVerified } from '@/stores/app'
</script>

<template>
  <div class="shell mobile">
    <header class="m-header">
      <router-link to="/" class="m-brand">🍜 今天吃什么</router-link>
      <router-link :to="isLoggedIn ? '/me' : '/login'" class="m-user">
        <van-tag v-if="isVerified" type="success" round>已认证</van-tag>
        <van-tag v-else-if="isLoggedIn" round color="#f6e7d6" text-color="#b5673f">未核验</van-tag>
        <van-tag v-else round color="#ece1c4" text-color="#6f5544">登录</van-tag>
      </router-link>
    </header>

    <main class="m-main">
      <router-view />
    </main>

    <van-tabbar route :border="false" active-color="#9a5230" inactive-color="#8d7663" safe-area-inset-bottom>
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
  height: 52px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(170, 181, 154, 0.9);
  backdrop-filter: saturate(160%) blur(12px);
  border-bottom: 1px dashed rgba(244, 237, 217, 0.6);
  padding-top: env(safe-area-inset-top);
}

.m-brand {
  font-family: var(--font-hand);
  font-size: 18px;
  font-weight: 700;
  color: var(--kraft-deep);
}

.m-user {
  display: flex;
  align-items: center;
}

.m-main {
  padding-bottom: 64px;
}

/* 底部 tabbar 米白纸条感 */
:deep(.van-tabbar) {
  background: var(--cream);
  box-shadow: 0 -4px 16px rgba(84, 56, 42, 0.12);
}

:deep(.van-tabbar-item__text) {
  font-family: var(--font-hand);
  font-size: 12px;
}
</style>
